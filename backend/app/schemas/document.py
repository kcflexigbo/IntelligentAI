from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from app.db.models import FileType

class DocumentResponse(BaseModel):
    """
    Pydantic schema for the response after a document is uploaded.
    """
    id: int
    filename: str
    uploaded_at: datetime
    user_id: Optional[int]  # Can be None for course materials
    file_type: FileType
    s3_key: Optional[str] = None
    transcription: Optional[str] = None
    is_course_material: bool = False
    course_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UploadUrlRequest(BaseModel):
    """Request schema for getting upload URL."""
    filename: str
    conversation_id: int
    content_type: Optional[str] = None


class UploadUrlResponse(BaseModel):
    """Response schema for upload URL."""
    upload_url: str
    s3_key: str
    expires_in: int


class ProcessUploadedFileRequest(BaseModel):
    """Request schema for processing an uploaded file."""
    s3_key: str
    filename: str
    conversation_id: int
