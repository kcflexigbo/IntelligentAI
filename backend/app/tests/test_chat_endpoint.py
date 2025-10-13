import pytest
from unittest.mock import AsyncMock

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.services import agent_service # We need to access the agent service to mock it
from app.services.rag_service import embeddings # To create a real embedding for the test

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

async def test_chat_endpoint_retrieves_and_generates(
    client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests the full RAG flow from the /chat endpoint.
    - Seeds the database with a specific document chunk.
    - Mocks the LLM call to return a predictable response.
    - Verifies that the correct context is retrieved and a valid answer is returned.
    """
    # --- 1. SETUP: Seed the database with a test document and user ---
    
    # Create user and document
    test_user = models.User(id=1, email="test@example.com", hashed_password="fake")
    test_doc = models.Document(id=1, filename="test.txt", user_id=1)
    db_session.add_all([test_user, test_doc])
    await db_session.commit()

    # Create a specific document chunk with known content
    chunk_content = "LangGraph is a library for building stateful, multi-actor applications with LLMs."
    chunk_embedding = embeddings.embed_query(chunk_content) # Use the real embedding model

    test_chunk = models.DocumentChunk(
        document_id=1,
        content=chunk_content,
        embedding=chunk_embedding
    )
    db_session.add(test_chunk)
    await db_session.commit()

    # --- 2. MOCKING: Replace the LLM call with a fake one ---

    # Define the mock answer we expect the LLM to generate
    mock_answer = agent_service.RAGAnswer(
        answer="LangGraph is a tool for creating agentic applications using LLMs."
    )
    
    # Create an async mock function that will replace the real rag_chain.ainvoke
    mock_rag_chain_ainvoke = AsyncMock(return_value=mock_answer)
    
    # Use pytest's monkeypatch to replace the entire rag_chain with a mock
    mock_chain = AsyncMock()
    mock_chain.ainvoke = mock_rag_chain_ainvoke
    monkeypatch.setattr(agent_service, "rag_chain", mock_chain)

    # --- 3. ACTION: Call the chat endpoint ---
    
    user_question = "What is LangGraph?"
    request_data = {"question": user_question, "session_id": "test_session_1"}
    
    response = await client.post("/chat", json=request_data)

    # --- 4. ASSERTIONS & VERIFICATION ---
    
    # Check the API response
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == mock_answer.answer
    
    # Verify that the correct context was retrieved and passed to the LLM
    assert len(data["retrieved_context"]) > 0
    assert data["retrieved_context"][0] == chunk_content

    # Verify that our mock LLM chain was called correctly
    mock_rag_chain_ainvoke.assert_called_once()
    
    # Inspect the arguments passed to the mocked function
    call_args, _ = mock_rag_chain_ainvoke.call_args
    passed_context = call_args[0]["context"]
    assert chunk_content in passed_context
    assert call_args[0]["question"] == user_question