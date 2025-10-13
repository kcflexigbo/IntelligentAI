# backend/app/services/agent_service.py
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.rag_service import embeddings # Reuse the same embedding model
from app.db import models

# --- 1. DEFINE AGENT STATE ---

class RAGState(TypedDict):
    """
    Represents the state of our RAG pipeline.
    """
    question: str
    context: List[str]
    answer: str

# --- 2. CONFIGURE LLM and PROMPT ---

# Initialize the LLM using your provider's details
llm = ChatOpenAI(
    model=settings.LLM_MODEL_NAME,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0.7,
)

# Define the prompt template for the generation step
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an intelligent learning assistant. Use the following retrieved context to answer the user's question. "
            "If the context doesn't contain the answer, state that you couldn't find the information in the provided documents. "
            "Be concise and helpful.\n\nCONTEXT:\n{context}",
        ),
        ("human", "{question}"),
    ]
)

# Define the output structure we want from the LLM
class RAGAnswer(BaseModel):
    """The final answer to the user's question."""
    answer: str = Field(description="The final answer to the user's question.")

# Chain the prompt, LLM, and output parser together
rag_chain = prompt | llm.with_structured_output(RAGAnswer)


# --- 3. DEFINE GRAPH NODES ---

async def retrieve_documents(state: RAGState, db: AsyncSession) -> RAGState:
    """
    Node to retrieve relevant documents from the database.
    """
    print("---RETRIEVING DOCUMENTS---")
    question = state["question"]
    
    # Create an embedding for the user's question
    question_embedding = embeddings.embed_query(question)
    
    # Query the database for the 5 most similar chunks
    # We use the L2 distance operator (<->) from pgvector
    query = (
        select(models.DocumentChunk)
        .order_by(models.DocumentChunk.embedding.l2_distance(question_embedding))
        .limit(5)
    )
    result = await db.execute(query)
    retrieved_docs = result.scalars().all()
    
    retrieved_context = [doc.content for doc in retrieved_docs]
    
    return {**state, "context": retrieved_context}

async def generate_answer(state: RAGState) -> RAGState:
    """
    Node to generate an answer using the LLM.
    """
    print("---GENERATING ANSWER---")
    question = state["question"]
    context = state["context"]
    
    # Invoke the RAG chain
    response = await rag_chain.ainvoke({"question": question, "context": "\n---\n".join(context)})
    
    return {**state, "answer": response.answer}

# --- 4. BUILD THE GRAPH ---

def create_retrieve_node(db: AsyncSession):
    """
    Factory function to create a retrieve node with db session closure.
    """
    async def retrieve_node(state: RAGState) -> RAGState:
        """
        Node to retrieve relevant documents from the database.
        """
        return await retrieve_documents(state, db)
    
    return retrieve_node

# --- 5. EXPOSED SERVICE FUNCTION ---

async def invoke_agent(question: str, db: AsyncSession) -> dict:
    """
    Main function to run the RAG agent.
    """
    # Initialize the graph
    workflow = StateGraph(RAGState)
    
    # Add the nodes
    workflow.add_node("retrieve", create_retrieve_node(db))
    workflow.add_node("generate", generate_answer)
    
    # Define the edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    
    # Compile the graph
    app = workflow.compile()
    
    initial_state: RAGState = {"question": question, "context": [], "answer": ""}
    final_state = await app.ainvoke(initial_state)
    return final_state