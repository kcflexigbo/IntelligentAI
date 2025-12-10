import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import models
from app.schemas.document import (
    DocumentResponse, 
    UploadUrlRequest, 
    UploadUrlResponse,
    ProcessUploadedFileRequest
)
from app.services import rag_service
from app.services import s3_service
from app.services import image_service
from app.services import video_service
from sqlalchemy import select, insert
from app.services.auth_service import get_current_user

router = APIRouter()

# File type detection
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v'}


def detect_file_type(filename: str) -> models.FileType:
    """Detect file type based on extension."""
    ext = os.path.splitext(filename.lower())[1]
    if ext in IMAGE_EXTENSIONS:
        return models.FileType.IMAGE
    elif ext in VIDEO_EXTENSIONS:
        return models.FileType.VIDEO
    else:
        return models.FileType.TEXT


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    request: UploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a presigned URL for uploading a file directly to S3.
    Frontend should upload to this URL, then call /process-upload to process the file.
    """
    # Verify conversation exists and belongs to user
    conv_res = await db.execute(
        select(models.Conversation).where(
            models.Conversation.id == request.conversation_id,
            models.Conversation.user_id == current_user.id
        )
    )
    conversation = conv_res.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")
    
    # Generate S3 key
    file_ext = os.path.splitext(request.filename)[1]
    unique_id = str(uuid.uuid4())
    s3_key = f"{current_user.id}/uploads/{unique_id}{file_ext}"
    
    # Generate presigned upload URL
    content_type = request.content_type or "application/octet-stream"
    upload_url = await s3_service.get_presigned_upload_url(s3_key, content_type, expires_in=3600)
    
    return UploadUrlResponse(
        upload_url=upload_url,
        s3_key=s3_key,
        expires_in=3600
    )


@router.post("/process-upload", response_model=DocumentResponse)
async def process_uploaded_file(
    request: ProcessUploadedFileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Process a file that was already uploaded to S3.
    This endpoint downloads the file from S3, processes it (OCR/transcription),
    creates embeddings, and associates it with the conversation.
    """
    # 1. Verify that the conversation exists and belongs to the user
    conv_res = await db.execute(
        select(models.Conversation).where(
            models.Conversation.id == request.conversation_id,
            models.Conversation.user_id == current_user.id
        )
    )
    conversation = conv_res.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    # 2. Verify S3 key belongs to this user
    if not request.s3_key.startswith(f"{current_user.id}/"):
        raise HTTPException(status_code=403, detail="Invalid S3 key - access denied.")
    
    # 3. Download file from S3
    try:
        file_content = await s3_service.download_file(request.s3_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in S3 storage.")
    
    # 4. Detect file type
    file_type = detect_file_type(request.filename)
    
    # 5. Process media files (OCR for images, transcription for videos)
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

    # 6. Create the document record
    document = models.Document(
        filename=request.filename,
        user_id=current_user.id,
        file_type=file_type,
        s3_key=request.s3_key,
        transcription=transcription,
        is_course_material=False
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # 7. Create the association between the document and the conversation
    await db.execute(
        insert(models.conversation_document_link).values(
            conversation_id=request.conversation_id,
            document_id=document.id
        )
    )
    await db.commit()

    # 8. Process and embed the document (async - don't block response)
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

    # 9. Return the response
    result = await db.execute(select(models.Document).where(models.Document.id == document.id))
    refreshed_document = result.scalar_one()
    
    return DocumentResponse.model_validate(refreshed_document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a user's own document.
    Only the document owner can delete their documents.
    """
    # Fetch the document
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Verify the document belongs to the current user
    if document.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. You can only delete your own documents.")
    
    # Verify it's not a course material (should use course-materials endpoint for those)
    if document.is_course_material:
        raise HTTPException(status_code=403, detail="Cannot delete course materials through this endpoint. Use /course-materials/{document_id} instead.")
    
    # Delete file from S3 if s3_key exists
    if document.s3_key:
        try:
            await s3_service.delete_file(document.s3_key)
        except Exception as e:
            # Log error but don't fail - document will still be deleted from DB
            print(f"Warning: Failed to delete file from S3: {e}")
    
    # Delete the document record (cascades will handle chunks and conversation links)
    await db.delete(document)
    await db.commit()
    
    return