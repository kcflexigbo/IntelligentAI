from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain_community.document_compressors import DocumentCompressorPipeline
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.tools import BaseTool
from typing import Type

# Depend on the robust functions from our vectordb core module
from ..core import vectordb

# --- Singleton Resource Management ---
print("Loading Cross-Encoder model for re-ranking...")
rerank_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
print("Cross-Encoder model loaded.")


class RerankRetrieveInput(BaseModel):
    """
    Input schema for the LLM. The model should only generate the search query.
    """
    query: str = Field(
        description="A detailed search query to find the most relevant course materials."
    )

class RerankRetrieveTool(BaseTool):
    """
    A tool that retrieves documents and then re-ranks them for maximum relevance
    to answer a student's question accurately.
    """
    name: str = "retrieve_and_rerank_material"
    description: str = (
        "Use this for complex questions that require high-accuracy retrieval from course materials. "
        "It finds relevant documents and then re-ranks them to ensure the best context is used."
    )
    args_schema: Type[RerankRetrieveInput] = RerankRetrieveInput

    def _run(self, *args, **kwargs):
        raise NotImplementedError("This tool does not support synchronous execution.")

    async def _arun(self, query: str, user_id: str) -> str:
        """
        Asynchronously retrieves and re-ranks documents.
        The `user_id` is injected by the agent's state.
        """
        if not user_id:
            return "Error: User context is missing. Cannot perform retrieval."

        collection_name = f"user_{user_id}"
        
        # 1. Base Retriever: Fetches a larger set of initial documents (e.g., top 10).
        base_retriever = vectordb.get_langchain_retriever(
            collection_name, 
            k=10 # Retrieve more documents initially for the re-ranker to process
        )

        if base_retriever is None:
            return "No learning materials found. Please upload documents first."
            
        # 2. Compressor Pipeline: This is where the re-ranking happens.
        # The CrossEncoderReranker will re-order the 10 documents from the base retriever.
        compressor = DocumentCompressorPipeline(
            transformers=[rerank_model]
        )
        
        # 3. Contextual Compression Retriever: Chains the base retriever and the re-ranker.
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor, 
            base_retriever=base_retriever
        )
        
        print(f"Retrieving and re-ranking documents for user '{user_id}' with query: '{query}'")
        # Invoking this retriever will automatically perform the fetch-then-rerank process.
        reranked_docs = await compression_retriever.ainvoke(query)

        if not reranked_docs:
            return "No relevant course material found after re-ranking."

        # We will return the top 3 most relevant documents after re-ranking.
        top_docs = reranked_docs[:3]

        formatted_docs = "\n\n---\n\n".join(
            [f"Source {i+1} (Top Relevance):\n{doc.page_content}" for i, doc in enumerate(top_docs)]
        )
        return f"Found highly relevant materials to answer the question:\n{formatted_docs}"