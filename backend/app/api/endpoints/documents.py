from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import models
from app.schemas.document import DocumentResponse
from app.services import rag_service
from sqlalchemy import select, insert
from app.services.auth_service import get_current_user

router = APIRouter()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    conversation_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint to upload a document and associate it with a specific conversation.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")
    
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 1. Verify that the conversation exists and belongs to the user
    conv_res = await db.execute(
        select(models.Conversation).where(
            models.Conversation.id == conversation_id,
            models.Conversation.user_id == current_user.id
        )
    )
    conversation = conv_res.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found or access denied.")

    # 2. Create the document record
    document = models.Document(
        filename=file.filename,
        user_id=current_user.id
    )
    db.add(document)
    await db.commit()
    await db.refresh(document) # Refresh to get the auto-generated ID

    # 3. Create the association between the document and the conversation
    # Avoid lazy-loading relationship access on an async session (which can trigger
    # IO in a context that raises MissingGreenlet). Instead, insert directly into
    # the association table to link the conversation and document.
    await db.execute(
        insert(models.conversation_document_link).values(
            conversation_id=conversation_id,
            document_id=document.id
        )
    )
    await db.commit()

    # 4. Trigger the background processing to chunk and embed the document
    await rag_service.process_and_embed_document(
        db=db,
        document_record=document,
        file_content=file_content,
        filename=file.filename
    )

    # 5. Return the response
    result = await db.execute(select(models.Document).where(models.Document.id == document.id))
    refreshed_document = result.scalar_one()
    
    # Use Pydantic's attribute-based model validation (models configured with from_attributes)
    return DocumentResponse.model_validate(refreshed_document)