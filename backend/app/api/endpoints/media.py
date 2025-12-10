"""
Media endpoints for retrieving files from S3/MinIO.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.services import s3_service

router = APIRouter()


@router.get("/{document_id}")
async def get_media_url(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a presigned URL for accessing a media file.
    Verifies that the user has access to the document.
    """
    # Fetch the document
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Check access: user must own the document OR it must be a course material
    has_access = (
        document.user_id == current_user.id or
        document.is_course_material == True
    )
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied to this document.")
    
    if not document.s3_key:
        raise HTTPException(status_code=404, detail="File not found in storage.")
    
    # Generate presigned URL (valid for 1 hour)
    try:
        url = await s3_service.get_presigned_url(document.s3_key, expires_in=3600)
        return {"url": url, "filename": document.filename, "file_type": document.file_type.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate access URL: {str(e)}")


@router.get("/{document_id}/download")
async def download_media(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Download a media file directly.
    Verifies that the user has access to the document.
    """
    # Fetch the document
    result = await db.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Check access: user must own the document OR it must be a course material
    has_access = (
        document.user_id == current_user.id or
        document.is_course_material == True
    )
    
    if not has_access:
        raise HTTPException(status_code=403, detail="Access denied to this document.")
    
    if not document.s3_key:
        raise HTTPException(status_code=404, detail="File not found in storage.")
    
    # Download file from S3
    try:
        from fastapi.responses import StreamingResponse
        import io
        
        file_content = await s3_service.download_file(document.s3_key)
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={document.filename}"
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in storage.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


