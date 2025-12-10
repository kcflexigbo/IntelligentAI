from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List
from app.db.models import FileType


class CourseResponse(BaseModel):
    """Response schema for course information."""
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseMaterialUploadUrlRequest(BaseModel):
    """Request schema for getting upload URL for course materials."""
    filename: str
    content_type: Optional[str] = None


class CourseMaterialProcessRequest(BaseModel):
    """Request schema for processing an uploaded course material file."""
    s3_key: str
    filename: str


class DocumentWithCourseResponse(BaseModel):
    """Document response with course information included."""
    id: int
    filename: str
    uploaded_at: datetime
    user_id: Optional[int]
    file_type: FileType
    s3_key: Optional[str] = None
    transcription: Optional[str] = None
    is_course_material: bool = False
    course_id: Optional[int] = None
    course_name: Optional[str] = None  # Course name for badge display

    model_config = ConfigDict(from_attributes=True)

