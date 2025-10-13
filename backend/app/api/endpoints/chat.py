from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import agent_service

router = APIRouter()

@router.post("", response_model=ChatResponse)
async def get_chat_response(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a response from the RAG agent.
    """
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    
    if not db:
        raise HTTPException(status_code=500, detail="Database session not available.")

    try:
        # Invoke the agent with the user's question
        final_state = await agent_service.invoke_agent(request.question, db)
        
        return ChatResponse(
            answer=final_state.get("answer", "Sorry, I couldn't process your request."),
            retrieved_context=final_state.get("context", [])
        )
    except Exception as e:
        print(f"Error invoking agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to get a response from the agent.")