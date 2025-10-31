from pydantic import BaseModel, ConfigDict
from datetime import datetime

class ConversationBase(BaseModel):
    title: str

# --- ADD THIS NEW SCHEMA ---
class ConversationUpdate(BaseModel):
    title: str

class ConversationCreate(BaseModel):
    pass

class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    is_from_user: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)