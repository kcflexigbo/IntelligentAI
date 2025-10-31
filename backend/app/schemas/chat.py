from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    """
    Schema for an incoming chat question.
    The session_id is no longer needed in the body.
    """
    question: str

class ChatResponse(BaseModel):
    """
    Schema for the response from the chat agent.
    """
    answer: str
    retrieved_context: List[str]
    rewritten_question: Optional[str] = None