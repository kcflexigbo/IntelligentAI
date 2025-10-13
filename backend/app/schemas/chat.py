from pydantic import BaseModel
from typing import List, Optional 

class ChatRequest(BaseModel):
    """
    Schema for an incoming chat question.
    """
    question: str
    session_id: str  # To track conversation history later

class ChatResponse(BaseModel):
    """
    Schema for the response from the chat agent.
    """
    answer: str
    retrieved_context: List[str]
    rewritten_question: Optional[str] = None