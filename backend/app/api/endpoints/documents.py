from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db import models
from app.schemas.document import DocumentResponse
from app.services import rag_service
from sqlalchemy import select
from app.services.auth_service import get_current_user

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint to upload a document.
    It creates a document record and triggers the background processing.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    # Read the content of the uploaded file
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- 1. Create the initial Document record ---
    # We save the document metadata first.
    document = models.Document(
        filename=file.filename,
        user_id=current_user.id
    )
    db.add(document)
    await db.commit()
    await db.refresh(document) # Refresh to get the auto-generated ID

    # Store the document ID before processing (while still in session)
    document_id = document.id
    
    # --- 2. Trigger the processing and embedding ---
    # This function handles the heavy lifting: chunking, embedding, and storing.
    await rag_service.process_and_embed_document(
        db=db,
        document_record=document,
        file_content=file_content,
        filename=file.filename
    )

    # Re-query the document to get a fresh instance attached to the current session
    # This prevents lazy-loading issues when FastAPI serializes the response
    result = await db.execute(select(models.Document).where(models.Document.id == document_id))
    refreshed_document = result.scalar_one()
    
    # Create response using the refreshed document
    response_data = DocumentResponse(
        id=refreshed_document.id,
        filename=refreshed_document.filename,
        uploaded_at=refreshed_document.uploaded_at,
        user_id=refreshed_document.user_id
    )
    
    return response_data