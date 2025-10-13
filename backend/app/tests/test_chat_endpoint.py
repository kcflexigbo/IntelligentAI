import pytest
from unittest.mock import AsyncMock, call

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import models
from app.services import agent_service
from app.services.rag_service import embeddings
from langchain_core.messages import HumanMessage, AIMessage # <-- Import message types

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

async def test_chat_endpoint_retrieves_and_generates(
    authenticated_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests the full RAG flow from the /chat endpoint.
    - Seeds the database with a specific document chunk.
    - Mocks the LLM call to return a predictable response.
    - Verifies that the correct context is retrieved and a valid answer is returned.
    """
    # --- 1. SETUP: Seed the database with a test document and user ---
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    test_doc = models.Document(id=1, filename="test.txt", user_id=test_user.id)
    db_session.add(test_doc)
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
    
    response = await authenticated_client.post("/chat", json=request_data)

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


async def test_chat_with_history_rewrites_question(
    authenticated_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests that the agent uses chat history to rewrite a follow-up question.
    """
    # --- 1. SETUP: Seed database with a user, document, and prior conversation ---
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    session_id = "test_conversation_123"
    test_doc = models.Document(id=1, filename="test.txt", user_id=test_user.id)
    db_session.add(test_doc)
    prior_user_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="What is LangGraph?", is_from_user=True
    )
    prior_ai_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="It is a library for building agents.", is_from_user=False
    )
    db_session.add_all([test_user, test_doc])

    # Add a previous turn to the chat history
    prior_user_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="What is LangGraph?", is_from_user=True
    )
    prior_ai_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="It is a library for building agents.", is_from_user=False
    )
    db_session.add_all([prior_user_msg, prior_ai_msg])
    await db_session.commit()

    # Add the document chunk that should be retrieved
    chunk_content = "LangGraph is primarily used for creating cyclical graphs for agent runtimes."
    chunk_embedding = embeddings.embed_query(chunk_content)
    test_chunk = models.DocumentChunk(
        document_id=1, content=chunk_content, embedding=chunk_embedding
    )
    db_session.add(test_chunk)
    await db_session.commit()

    # --- 2. MOCKING: Mock both the rewriter and the RAG chain ---

    # Mock the rewriter chain
    rewritten_question = "What is LangGraph used for?"
    mock_rewriter_answer = agent_service.RewrittenQuestion(
        rewritten_question=rewritten_question
    )
    mock_rewriter_chain_ainvoke = AsyncMock(return_value=mock_rewriter_answer)
    mock_rewriter_chain = AsyncMock()
    mock_rewriter_chain.ainvoke = mock_rewriter_chain_ainvoke
    monkeypatch.setattr(agent_service, "rewriter_chain", mock_rewriter_chain)

    # Mock the final RAG answer chain
    final_answer = "LangGraph is used for creating agent runtimes."
    mock_rag_answer = agent_service.RAGAnswer(answer=final_answer)
    mock_rag_chain_ainvoke = AsyncMock(return_value=mock_rag_answer)
    mock_rag_chain = AsyncMock()
    mock_rag_chain.ainvoke = mock_rag_chain_ainvoke
    monkeypatch.setattr(agent_service, "rag_chain", mock_rag_chain)

    # --- 3. ACTION: Ask a follow-up question ---
    follow_up_question = "what is it used for?"
    response = await authenticated_client.post(
        "/chat",
        json={"question": follow_up_question, "session_id": session_id},
    )

    # --- 4. ASSERTIONS & VERIFICATION ---

    # Check the API response
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == final_answer
    assert data["rewritten_question"] == rewritten_question

    # Verify the rewriter was called correctly
    mock_rewriter_chain_ainvoke.assert_called_once()
    rewriter_call_args = mock_rewriter_chain_ainvoke.call_args[0][0]
    assert rewriter_call_args["question"] == follow_up_question
    # Check that the history was passed in
    assert len(rewriter_call_args["chat_history"]) == 2
    assert rewriter_call_args["chat_history"][0].content == "What is LangGraph?"

    # Verify the RAG chain was called with context retrieved using the REWRITTEN question
    mock_rag_chain_ainvoke.assert_called_once()
    rag_call_args = mock_rag_chain_ainvoke.call_args[0][0]
    assert rag_call_args["question"] == follow_up_question # Uses original question for final answer
    assert chunk_content in rag_call_args["context"]

    # Verify that the new conversation turn was saved to the database
    result = await db_session.execute(
        select(models.ChatMessage)
        .where(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at)
    )
    all_messages = result.scalars().all()
    assert len(all_messages) == 4 # 2 old messages + 2 new ones
    assert all_messages[2].content == follow_up_question
    assert all_messages[2].is_from_user is True
    assert all_messages[3].content == final_answer
    assert all_messages[3].is_from_user is False


async def test_chat_with_reranking_filters_documents(
    authenticated_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests that the grading and re-ranking step correctly filters out
    irrelevant documents before the final generation.
    """
    # --- 1. SETUP: Seed DB with a relevant and an irrelevant chunk ---
    session_id = "test_reranking_session"
    user_question = "What is the purpose of LangGraph?"
    
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    session_id = "test_reranking_session"
    test_doc = models.Document(id=1, filename="test.txt", user_id=test_user.id)
    db_session.add(test_doc)
    await db_session.commit()

    # This chunk is highly relevant and should be kept
    relevant_content = "LangGraph is a library for building stateful, multi-actor applications with LLMs, used for agentic architectures."
    relevant_embedding = embeddings.embed_query(relevant_content)
    relevant_chunk = models.DocumentChunk(
        document_id=1, content=relevant_content, embedding=relevant_embedding
    )

    # This chunk is semantically similar (contains 'graph') but not relevant
    irrelevant_content = "Graph theory is the study of mathematical structures used to model pairwise relations between objects."
    irrelevant_embedding = embeddings.embed_query(irrelevant_content)
    irrelevant_chunk = models.DocumentChunk(
        document_id=1, content=irrelevant_content, embedding=irrelevant_embedding
    )
    
    db_session.add_all([relevant_chunk, irrelevant_chunk])
    await db_session.commit()

    # --- 2. MOCKING: Mock the rewriter, grader, and final answer chains ---

    # Mock the rewriter to return the question as-is
    mock_rewriter_ainvoke = AsyncMock(
        return_value=agent_service.RewrittenQuestion(rewritten_question=user_question)
    )
    mock_rewriter_chain = AsyncMock()
    mock_rewriter_chain.ainvoke = mock_rewriter_ainvoke
    monkeypatch.setattr(agent_service, "rewriter_chain", mock_rewriter_chain)

    # Mock the grading chain with a side_effect to return different values
    async def grading_side_effect(inputs):
        doc_content = inputs["document"]
        if "LangGraph" in doc_content:
            return agent_service.GradeDocuments(binary_score="yes")
        else:
            return agent_service.GradeDocuments(binary_score="no")

    mock_grading_ainvoke = AsyncMock(side_effect=grading_side_effect)
    mock_grading_chain = AsyncMock()
    mock_grading_chain.ainvoke = mock_grading_ainvoke
    monkeypatch.setattr(agent_service, "grading_chain", mock_grading_chain)

    # Mock the final RAG answer chain
    final_answer = "LangGraph is for building agentic applications."
    mock_rag_ainvoke = AsyncMock(
        return_value=agent_service.RAGAnswer(answer=final_answer)
    )
    mock_rag_chain = AsyncMock()
    mock_rag_chain.ainvoke = mock_rag_ainvoke
    monkeypatch.setattr(agent_service, "rag_chain", mock_rag_chain)

    # --- 3. ACTION: Call the chat endpoint ---
    response = await authenticated_client.post(
        "/chat",
        json={"question": user_question, "session_id": session_id},
    )

    # --- 4. ASSERTIONS & VERIFICATION ---

    # Check the API response
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == final_answer

    # Verify the grading chain was called for both documents
    assert mock_grading_ainvoke.call_count == 2

    # Verify the final RAG chain was called ONLY with the relevant context
    mock_rag_ainvoke.assert_called_once()
    rag_call_args = mock_rag_ainvoke.call_args[0][0]
    
    # THE CRITICAL ASSERTION:
    # The context passed to the final LLM should contain the relevant content
    # and MUST NOT contain the irrelevant content.
    final_context = rag_call_args["context"]
    assert relevant_content in final_context
    assert irrelevant_content not in final_context

    # Verify that the new conversation was saved correctly
    result = await db_session.execute(
        select(models.ChatMessage).where(models.ChatMessage.session_id == session_id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2
    assert messages[1].content == final_answer