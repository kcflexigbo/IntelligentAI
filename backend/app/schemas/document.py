from pydantic import BaseModel, ConfigDict
from datetime import datetime

class DocumentResponse(BaseModel):
    """
    Pydantic schema for the response after a document is uploaded.
    """
    id: int
    filename: str
    uploaded_at: datetime
    user_id: int

    model_config = ConfigDict(from_attributes=True)