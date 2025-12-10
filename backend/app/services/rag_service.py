import os
from tempfile import NamedTemporaryFile
from typing import List

from langchain_community.document_loaders import PyPDFLoader
import warnings

from langchain_unstructured import UnstructuredLoader as UnstructuredFileLoader  # type: ignore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models

# --- 1. CONFIGURE EMBEDDING MODEL & TEXT SPLITTER ---

# Initialize the embedding model.
# "all-MiniLM-L6-v2" is a fast and effective model for generating embeddings.
# It runs locally on your CPU.
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize the text splitter.
# This will break down large documents into smaller, manageable chunks.
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # The size of each chunk in characters
    chunk_overlap=100, # The number of characters to overlap between chunks
)

async def process_and_embed_document(
    db: AsyncSession,
    document_record: models.Document,
    file_content: bytes,
    filename: str
):
    """
    Processes an uploaded file, chunks it, creates embeddings, and stores them.

    Args:
        db: The database session.
        document_record: The SQLAlchemy Document model instance.
        file_content: The raw content of the file.
        filename: The name of the file to determine the loader.
    """
    # --- 2. LOAD THE DOCUMENT ---

    # Use a temporary file to handle the uploaded content
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        # Select the appropriate loader based on the file extension
        if filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(tmp_path)
        else:
            # UnstructuredFileLoader can handle .txt, .docx, .md, etc.
            loader = UnstructuredFileLoader(tmp_path)
        
        # Load the document pages/content
        docs = loader.load()

        # --- 3. SPLIT THE DOCUMENT INTO CHUNKS ---
        
        chunks = text_splitter.split_documents(docs)
        
        if not chunks:
            print("Warning: Document could not be split into chunks.")
            return

        # --- 4. CREATE EMBEDDINGS AND STORE IN DB ---

        # Prepare DocumentChunk objects for bulk insertion
        db_chunks: List[models.DocumentChunk] = []
        
        # Extract the text content from each chunk
        chunk_texts = [chunk.page_content for chunk in chunks]
        
        # Generate embeddings for all chunks in a single batch
        chunk_embeddings = embeddings.embed_documents(chunk_texts)

        for i, chunk in enumerate(chunks):
            db_chunks.append(
                models.DocumentChunk(
                    document_id=document_record.id,
                    content=chunk.page_content,
                    embedding=chunk_embeddings[i]
                )
            )
        
        # Add all the new chunks to the session and commit
        db.add_all(db_chunks)
        await db.commit()
        print(f"Successfully processed and stored {len(db_chunks)} chunks for document: {filename}")

    finally:
        # Clean up the temporary file
        os.remove(tmp_path)


async def process_text_content(
    db: AsyncSession,
    document_record: models.Document,
    text_content: str
):
    """
    Process text content (from OCR or transcription) and create embeddings.

    Args:
        db: The database session.
        document_record: The SQLAlchemy Document model instance.
        text_content: The text content to process and embed.
    """
    if not text_content or not text_content.strip():
        print("Warning: No text content to process.")
        return

    # Split the text into chunks
    chunks = text_splitter.split_text(text_content)
    
    if not chunks:
        print("Warning: Text could not be split into chunks.")
        return

    # Prepare DocumentChunk objects for bulk insertion
    db_chunks: List[models.DocumentChunk] = []
    
    # Generate embeddings for all chunks in a single batch
    chunk_embeddings = embeddings.embed_documents(chunks)

    for i, chunk_text in enumerate(chunks):
        db_chunks.append(
            models.DocumentChunk(
                document_id=document_record.id,
                content=chunk_text,
                embedding=chunk_embeddings[i]
            )
        )
    
    # Add all the new chunks to the session and commit
    db.add_all(db_chunks)
    await db.commit()
    print(f"Successfully processed and stored {len(db_chunks)} chunks for document: {document_record.filename}")