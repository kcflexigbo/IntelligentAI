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


class RAGState(TypedDict):
    """
    Represents the state of our RAG pipeline.
    """
    question: str
    chat_history: List[BaseMessage] # <-- Add chat history
    rewritten_question: str         # <-- Add rewritten question
    context: List[str]
    answer: str
    documents: List[models.DocumentChunk]

llm = ChatOpenAI(
    model=settings.LLM_MODEL_NAME,
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
    temperature=0.7,
)

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

class RAGAnswer(BaseModel):
    """The final answer to the user's question."""
    answer: str = Field(description="The final answer to the user's question.")

rag_chain = prompt | llm.with_structured_output(RAGAnswer)

class RewrittenQuestion(BaseModel):
    """The rewritten, standalone question."""
    rewritten_question: str = Field(description="The standalone version of the user's question.")

rewriter_chain = rewriter_prompt | llm.with_structured_output(RewrittenQuestion)

class GradeDocuments(BaseModel):
    """Binary score for document relevance."""
    binary_score: str = Field(
        description="Is the document relevant to the user's question? 'yes' or 'no'."
    )

grading_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a grader assessing the relevance of a retrieved document to a user question. "
            "If the document contains keywords or semantic meaning related to the question, grade it as relevant. "
            "Give a binary 'yes' or 'no' score to indicate whether the document is relevant.",
        ),
        ("human", "Retrieved Document:\n\n{document}\n\nUser Question: {question}"),
    ]
)

grading_chain = grading_prompt | llm.with_structured_output(GradeDocuments)



async def retrieve_node(state: RAGState, config: RunnableConfig) -> RAGState:
    """
    Node wrapper to retrieve documents with database session from config.
    """
    db = config.get("configurable", {}).get("db")
    return await retrieve_documents(state, db)

async def retrieve_documents(state: RAGState, db: AsyncSession) -> RAGState:
    """
    Node to retrieve documents. This now retrieves more documents initially
    and stores the full objects in the state.
    """
    print("---RETRIEVING DOCUMENTS---")
    question_for_retrieval = state["rewritten_question"]
    
    question_embedding = embeddings.embed_query(question_for_retrieval)
    
    query = (
        select(models.DocumentChunk)
        .order_by(models.DocumentChunk.embedding.l2_distance(question_embedding))
        .limit(10)
    )
    result = await db.execute(query)
    retrieved_docs = result.scalars().all()
    
    return {**state, "documents": retrieved_docs}


async def rewrite_query(state: RAGState) -> RAGState:
    """
    Node to rewrite the user's question based on chat history.
    """
    print("---REWRITING QUESTION---")
    question = state["question"]
    chat_history = state["chat_history"]

    if not chat_history:
        return {**state, "rewritten_question": question}

    response = await rewriter_chain.ainvoke(
        {"question": question, "chat_history": chat_history}
    )
    return {**state, "rewritten_question": response.rewritten_question}

async def grade_documents(state: RAGState) -> RAGState:
    """
    Node to grade the relevance of retrieved documents.
    """
    print("---GRADING DOCUMENTS---")
    question = state["rewritten_question"]
    documents_to_grade = state["documents"]
    
    # Grade all documents in parallel
    async def grade_single_doc(doc):
        result = await grading_chain.ainvoke({"question": question, "document": doc.content})
        is_relevant = result.binary_score.lower() == "yes"
        if is_relevant:
            print(f"---Document ID {doc.id} is RELEVANT---")
        else:
            print(f"---Document ID {doc.id} is NOT RELEVANT---")
        return (doc, is_relevant)
    
    # Execute all grading tasks concurrently
    import asyncio
    grading_results = await asyncio.gather(*[grade_single_doc(doc) for doc in documents_to_grade])
    
    # Filter to keep only relevant documents
    relevant_docs = [doc for doc, is_relevant in grading_results if is_relevant]
            
    return {**state, "documents": relevant_docs}

async def generate_answer(state: RAGState) -> RAGState:
    """
    Node to generate an answer. This now gets its context from the
    filtered 'documents' field.
    """
    print("---GENERATING ANSWER---")
    question = state["question"]
    context = [doc.content for doc in state["documents"]]
    
    response = await rag_chain.ainvoke({"question": question, "context": "\n---\n".join(context)})
    
    return {**state, "answer": response.answer, "context": context}

def decide_to_generate(state: RAGState) -> str:
    """
    Conditional edge logic. If relevant documents are found, generate an answer.
    Otherwise, end the process with a fallback message.
    """
    print("---ASSESSING RELEVANCE---")
    if not state["documents"]:
        print("---No relevant documents found. Ending with fallback.---")
        fallback_answer = "I could not find any relevant information in the provided documents to answer your question."
        return "end_with_fallback"
    else:
        return "generate"


workflow = StateGraph(RAGState)

workflow.add_node("rewrite", rewrite_query)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade", grade_documents) 
workflow.add_node("generate", generate_answer)
# A special node for the fallback case
workflow.add_node("end_with_fallback", 
                  lambda state: {
                      **state, 
                      "answer": "I could not find any relevant information in the provided documents to answer your question.",
                        "context": []}
                )

workflow.set_entry_point("rewrite")
workflow.add_edge("rewrite", "retrieve")
workflow.add_edge("retrieve", "grade") 
workflow.add_conditional_edges(
    "grade", 
    decide_to_generate, 
    {
        "generate": "generate", 
        "end_with_fallback": "end_with_fallback" 
    }
)
workflow.add_edge("generate", END)
workflow.add_edge("end_with_fallback", END)

app = workflow.compile()

app.get_graph().draw_mermaid_png(
    output_file_path="rag_workflow.png"
)

async def invoke_agent(question: str, chat_history: List[BaseMessage], db: AsyncSession) -> dict:
    initial_state = {"question": question, "chat_history": chat_history}
    final_state = await app.ainvoke(initial_state, {"configurable": {"db": db}})
    return final_state