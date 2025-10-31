from pydantic import BaseModel, ConfigDict
from datetime import datetime

# Base schema for conversation properties
class ConversationBase(BaseModel):
    title: str

# Schema for creating a conversation (currently no input needed from user)
class ConversationCreate(BaseModel):
    pass

# Schema for the response when a conversation is returned
class ConversationResponse(ConversationBase):
    id: int
    user_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Schema for representing a single chat message in the history
class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    content: str
    is_from_user: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)