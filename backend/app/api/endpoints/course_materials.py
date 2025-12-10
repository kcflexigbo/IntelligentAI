import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.db.session import get_db
from app.db import models
from app.schemas.course import (
    CourseResponse,
    CourseMaterialUploadUrlRequest,
    CourseMaterialProcessRequest,
    DocumentWithCourseResponse
)
from app.schemas.document import UploadUrlResponse
from app.services import rag_service, s3_service, image_service, video_service, course_service
from app.services.auth_service import get_current_user
from app.api.endpoints.documents import detect_file_type

router = APIRouter()

# Default course name
DEFAULT_COURSE_NAME = "Introduction to Computer Science"


@router.get("", response_model=List[DocumentWithCourseResponse])
async def get_course_materials(
    course_id: Optional[int] = Query(None, description="Filter by course ID"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all course materials. Optionally filter by course_id.
    Returns documents with course information for badge display.
    """
    query = (
        select(models.Document)
        .options(selectinload(models.Document.course))
        .where(models.Document.is_course_material == True)
    )
    
    if course_id:
        query = query.where(models.Document.course_id == course_id)
    
    query = query.order_by(models.Document.uploaded_at.desc())
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    # Convert to response with course information
    response = []
    for doc in documents:
        doc_dict = {
            "id": doc.id,
            "filename": doc.filename,
            "uploaded_at": doc.uploaded_at,
            "user_id": doc.user_id,
            "file_type": doc.file_type,
            "s3_key": doc.s3_key,
            "transcription": doc.transcription,
            "is_course_material": doc.is_course_material,
            "course_id": doc.course_id,
            "course_name": doc.course.name if doc.course else None
        }
        response.append(DocumentWithCourseResponse(**doc_dict))
    
    return response


@router.get("/courses", response_model=List[CourseResponse])
async def get_courses(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all courses list.
    """
    query = select(models.Course).order_by(models.Course.created_at.desc())
    result = await db.execute(query)
    courses = result.scalars().all()
    return courses


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_course_material_upload_url(
    request: CourseMaterialUploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a presigned URL for uploading a course material file directly to S3.
    The file will be associated with the default course.
    Frontend should upload to this URL, then call /process-upload to process the file.
    """
    # Get or create the default course
    course = await course_service.get_or_create_course(
        db=db,
        name=DEFAULT_COURSE_NAME,
        description="Fundamental concepts in computer science including programming, algorithms, and data structures."
    )
    
    # Generate S3 key
    file_ext = os.path.splitext(request.filename)[1]
    unique_id = str(uuid.uuid4())
    s3_key = f"courses/{course.id}/materials/{unique_id}{file_ext}"
    
    # Generate presigned upload URL
    content_type = request.content_type or "application/octet-stream"
    upload_url = await s3_service.get_presigned_upload_url(s3_key, content_type, expires_in=3600)
    
    return UploadUrlResponse(
        upload_url=upload_url,
        s3_key=s3_key,
        expires_in=3600
    )


@router.post("/process-upload", response_model=DocumentWithCourseResponse)
async def process_course_material_upload(
    request: CourseMaterialProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process a course material file that was already uploaded to S3.
    This endpoint downloads the file from S3, processes it (OCR/transcription),
    creates embeddings, and associates it with the default course.
    """
    # Get or create the default course
    course = await course_service.get_or_create_course(
        db=db,
        name=DEFAULT_COURSE_NAME,
        description="Fundamental concepts in computer science including programming, algorithms, and data structures."
    )
    
    # Verify S3 key belongs to course materials
    if not request.s3_key.startswith(f"courses/{course.id}/materials/"):
        raise HTTPException(status_code=403, detail="Invalid S3 key - must be a course material.")
    
    # Download file from S3
    try:
        file_content = await s3_service.download_file(request.s3_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in S3 storage.")
    
    # Detect file type
    file_type = detect_file_type(request.filename)
    
    # Process media files (OCR for images, transcription for videos)
    extracted_text = None
    transcription = None
    
    if file_type == models.FileType.IMAGE:
        # Extract text using OCR
        extracted_text = await image_service.extract_text_from_image(file_content)
        transcription = extracted_text
        
    elif file_type == models.FileType.VIDEO:
        # Transcribe video
        transcription = await video_service.transcribe_video(file_content, request.filename)
        extracted_text = transcription

    # Create the document record as course material
    document = models.Document(
        filename=request.filename,
        user_id=None,  # Course materials don't belong to a user
        file_type=file_type,
        s3_key=request.s3_key,
        transcription=transcription,
        is_course_material=True,
        course_id=course.id
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Process and embed the document
    # For images/videos, use extracted text; for text files, process normally
    if file_type == models.FileType.TEXT:
        await rag_service.process_and_embed_document(
            db=db,
            document_record=document,
            file_content=file_content,
            filename=request.filename
        )
    elif extracted_text:
        await rag_service.process_text_content(
            db=db,
            document_record=document,
            text_content=extracted_text
        )

    # Return the response with course information
    await db.refresh(document)
    await db.refresh(course)
    
    return DocumentWithCourseResponse(
        id=document.id,
        filename=document.filename,
        uploaded_at=document.uploaded_at,
        user_id=document.user_id,
        file_type=document.file_type,
        s3_key=document.s3_key,
        transcription=document.transcription,
        is_course_material=document.is_course_material,
        course_id=document.course_id,
        course_name=course.name
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_material(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a course material.
    All logged-in users can delete course materials.
    """
    # Fetch the document
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Verify it's a course material
    if not document.is_course_material:
        raise HTTPException(status_code=403, detail="This is not a course material. Use /documents/{document_id} endpoint instead.")
    
    # Delete file from S3 if s3_key exists
    if document.s3_key:
        try:
            await s3_service.delete_file(document.s3_key)
        except Exception as e:
            # Log error but don't fail - document will still be deleted from DB
            print(f"Warning: Failed to delete file from S3: {e}")
    
    # Delete the document record (cascades will handle chunks)
    await db.delete(document)
    await db.commit()
    
    return

