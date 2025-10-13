import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import models

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

async def test_upload_document_and_process(
    authenticated_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests the entire document upload and processing flow.
    """
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    user_id = test_user.id

    # --- 2. ACTION: Upload a dummy text file ---
    dummy_file_content = "This is a test document for the learning assistant."
    files = {"file": ("test_doc.txt", dummy_file_content, "text/plain")}
    
    # The client will hit our endpoint, which uses a dummy get_current_user
    # that returns a user with id=1.
    response = await authenticated_client.post("/documents/upload", files=files)

    # --- 3. ASSERTIONS: Check the API response ---
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_doc.txt"
    assert data["user_id"] == user_id
    document_id = data["id"]

    # --- 4. VERIFICATION: Check the database content ---
    
    # Verify the Document record was created
    doc_result = await db_session.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc_in_db = doc_result.scalar_one_or_none()
    assert doc_in_db is not None
    assert doc_in_db.filename == "test_doc.txt"

    # Verify that DocumentChunks were created for this document
    chunk_result = await db_session.execute(
        select(models.DocumentChunk).where(models.DocumentChunk.document_id == document_id)
    )
    chunks_in_db = chunk_result.scalars().all()
    
    # Since the content is small, it should create exactly one chunk
    assert len(chunks_in_db) == 1
    
    # Verify the chunk content and embedding
    first_chunk = chunks_in_db[0]
    assert first_chunk.content == dummy_file_content
    assert first_chunk.embedding is not None
    
    # The embedding for "all-MiniLM-L6-v2" has 384 dimensions
    assert len(first_chunk.embedding) == 384