from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.db import models
from backend.app.schemas.document import DocumentResponse
from backend.app.services import rag_service

# --- DUMMY AUTH DEPENDENCY (to be replaced later) ---
# In a real application, this would come from your auth service.
# For now, we'll simulate a logged-in user.
async def get_current_user() -> models.User:
    # This is a placeholder. We will create a real user for testing.
    # In the future, this will decode a JWT token.
    return models.User(id=1, email="testuser@example.com")
# ---

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

    # --- 2. Trigger the processing and embedding ---
    # This function handles the heavy lifting: chunking, embedding, and storing.
    await rag_service.process_and_embed_document(
        db=db,
        document_record=document,
        file_content=file_content,
        filename=file.filename
    )

    return document