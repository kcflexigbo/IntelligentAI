from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_core.messages import HumanMessage, AIMessage

from app.db.session import get_db
from app.db import models
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.conversation import ConversationResponse, ChatMessageResponse
from app.services import agent_service
from app.services.auth_service import get_current_user

router = APIRouter()

@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Creates a new, empty conversation for the logged-in user.
    """
    new_conversation = models.Conversation(user_id=current_user.id, title="New Conversation")
    db.add(new_conversation)
    await db.commit()
    await db.refresh(new_conversation)
    return new_conversation

@router.get("", response_model=List[ConversationResponse])
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves all conversations for the logged-in user.
    """
    query = select(models.Conversation).where(models.Conversation.user_id == current_user.id).order_by(models.Conversation.created_at.desc())
    result = await db.execute(query)
    conversations = result.scalars().all()
    return conversations

@router.get("/{conversation_id}/messages", response_model=List[ChatMessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves all messages for a specific conversation.
    """
    query = select(models.ChatMessage).where(models.ChatMessage.conversation_id == conversation_id).order_by(models.ChatMessage.created_at)
    result = await db.execute(query)
    messages = result.scalars().all()
    
    # Ensure the conversation belongs to the user by checking the first message if it exists
    if messages and messages[0].conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this conversation")
        
    return messages

@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message_to_conversation(
    conversation_id: int,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Sends a message to a specific conversation and gets a response from the agent.
    """
    # Verify the conversation exists and belongs to the user
    conv_res = await db.execute(select(models.Conversation).where(models.Conversation.id == conversation_id))
    conversation = conv_res.scalar_one_or_none()

    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or access denied")

    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    try:
        # Fetch history for this specific conversation
        history_query = (
            select(models.ChatMessage)
            .where(models.ChatMessage.conversation_id == conversation_id)
            .order_by(models.ChatMessage.created_at)
        )
        result = await db.execute(history_query)
        db_messages = result.scalars().all()
        
        chat_history = [
            HumanMessage(content=msg.content) if msg.is_from_user else AIMessage(content=msg.content)
            for msg in db_messages
        ]

        # Invoke agent
        final_state = await agent_service.invoke_agent(request.question, chat_history, db)

        # Save user message
        user_message = models.ChatMessage(
            conversation_id=conversation_id,
            content=request.question,
            is_from_user=True
        )
        
        # Save AI message
        ai_answer = final_state.get("answer", "Sorry, I couldn't process your request.")
        ai_message = models.ChatMessage(
            conversation_id=conversation_id,
            content=ai_answer,
            is_from_user=False
        )
        
        db.add_all([user_message, ai_message])

        # If this is the first message, update the conversation title
        if not db_messages:
            conversation.title = request.question[:50] # Use first 50 chars as title

        await db.commit()

        return ChatResponse(
            answer=ai_answer,
            retrieved_context=final_state.get("context", []),
            rewritten_question=final_state.get("rewritten_question")
        )
    except Exception as e:
        print(f"Error invoking agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to get a response from the agent.")

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Deletes a conversation and all its messages.
    """
    conv_res = await db.execute(select(models.Conversation).where(models.Conversation.id == conversation_id))
    conversation = conv_res.scalar_one_or_none()
    
    if not conversation or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        
    await db.delete(conversation)
    await db.commit()
    return