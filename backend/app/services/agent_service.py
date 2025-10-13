from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage

from app.core.config import settings
from app.services.rag_service import embeddings # Reuse the same embedding model
from app.db import models

# --- 1. DEFINE AGENT STATE ---

class RAGState(TypedDict):
    """
    Represents the state of our RAG pipeline.
    """
    question: str
    chat_history: List[BaseMessage] # <-- Add chat history
    rewritten_question: str         # <-- Add rewritten question
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

rewriter_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a query rewriter. Given a chat history and a follow-up question, "
            "rephrase the follow-up question to be a standalone question that captures all relevant context. "
            "If the question is already standalone, return it unchanged.",
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{question}"),
    ]
)

# Define the output structure we want from the LLM
class RAGAnswer(BaseModel):
    """The final answer to the user's question."""
    answer: str = Field(description="The final answer to the user's question.")

# Chain the prompt, LLM, and output parser together
rag_chain = prompt | llm.with_structured_output(RAGAnswer)

class RewrittenQuestion(BaseModel):
    """The rewritten, standalone question."""
    rewritten_question: str = Field(description="The standalone version of the user's question.")

# Chain for the rewriter
rewriter_chain = rewriter_prompt | llm.with_structured_output(RewrittenQuestion)




# --- 3. DEFINE GRAPH NODES ---

async def rewrite_query(state: RAGState) -> RAGState:
    """
    Node to rewrite the user's question based on chat history.
    """
    print("---REWRITING QUESTION---")
    question = state["question"]
    chat_history = state["chat_history"]

    # If there's no history, the question is already standalone
    if not chat_history:
        return {**state, "rewritten_question": question}

    response = await rewriter_chain.ainvoke(
        {"question": question, "chat_history": chat_history}
    )
    return {**state, "rewritten_question": response.rewritten_question}


async def retrieve_documents(state: RAGState, db: AsyncSession) -> RAGState:
    """
    Node to retrieve relevant documents from the database using the rewritten question.
    """
    print("---RETRIEVING DOCUMENTS---")
    # --- THIS IS THE KEY CHANGE: Use the rewritten_question for retrieval ---
    question_for_retrieval = state["rewritten_question"]
    print(f"---Question for retrieval: {question_for_retrieval}---")
    
    question_embedding = embeddings.embed_query(question_for_retrieval)
    
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
    # --- Use the ORIGINAL question for the final answer ---
    # This gives the LLM the most direct version of what the user asked.
    question = state["question"]
    context = state["context"]
    
    response = await rag_chain.ainvoke({"question": question, "context": "\n---\n".join(context)})
    
    return {**state, "answer": response.answer}

async def retrieve_node(state: RAGState, config: RunnableConfig) -> RAGState:
    """
    Node wrapper to retrieve documents with database session from config.
    """
    db = config.get("configurable", {}).get("db")
    return await retrieve_documents(state, db)

# --- 4. BUILD THE GRAPH ---

workflow = StateGraph(RAGState)

# Add the nodes
workflow.add_node("rewrite", rewrite_query) # <-- Add new node
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_answer)

# Define the edges
workflow.set_entry_point("rewrite") # <-- Change entry point
workflow.add_edge("rewrite", "retrieve") # <-- New edge
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)

app = workflow.compile()

# --- 5. EXPOSED SERVICE FUNCTION ---

# Update the function signature to accept chat_history
async def invoke_agent(question: str, chat_history: List[BaseMessage], db: AsyncSession) -> dict:
    """
    Main function to run the RAG agent.
    """
    initial_state = {"question": question, "chat_history": chat_history}
    final_state = await app.ainvoke(initial_state, {"configurable": {"db": db}})
    return final_state