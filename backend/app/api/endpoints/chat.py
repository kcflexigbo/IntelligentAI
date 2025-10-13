# backend/app/api/endpoints/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_core.messages import HumanMessage, AIMessage # <-- Import message types

from app.db.session import get_db
from app.db import models # <-- Import models
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import agent_service
from app.api.endpoints.documents import get_current_user # <-- Reuse our dummy user auth

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def get_chat_response(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # <-- Get current user
):
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # 1. Fetch chat history for the session from the DB
        history_query = (
            select(models.ChatMessage)
            .where(models.ChatMessage.session_id == request.session_id)
            .where(models.ChatMessage.user_id == current_user.id)
            .order_by(models.ChatMessage.created_at)
        )
        result = await db.execute(history_query)
        db_messages = result.scalars().all()

        # 2. Format history for the agent
        chat_history = [
            HumanMessage(content=msg.content) if msg.is_from_user else AIMessage(content=msg.content)
            for msg in db_messages
        ]

        # 3. Invoke the agent
        final_state = await agent_service.invoke_agent(request.question, chat_history, db)
        
        # 4. Save the new messages to the database
        user_message = models.ChatMessage(
            session_id=request.session_id,
            user_id=current_user.id,
            content=request.question,
            is_from_user=True
        )
        ai_answer = final_state.get("answer", "Sorry, I couldn't process your request.")
        ai_message = models.ChatMessage(
            session_id=request.session_id,
            user_id=current_user.id,
            content=ai_answer,
            is_from_user=False
        )
        db.add_all([user_message, ai_message])
        await db.commit()

        return ChatResponse(
            answer=ai_answer,
            retrieved_context=final_state.get("context", []),
            rewritten_question=final_state.get("rewritten_question")
        )
    except Exception as e:
        print(f"Error invoking agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to get a response from the agent.")