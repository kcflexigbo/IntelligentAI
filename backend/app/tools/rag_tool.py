from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Type

# Depend on the robust functions from our vectordb core module
from ..core import vectordb

class RetrieveCourseMaterialInput(BaseModel):
    """
    Input schema for the LLM. The model should only generate the search query.
    """
    query: str = Field(
        description="A detailed search query to find relevant course materials based on the user's question."
    )

class RetrieveCourseMaterialTool(BaseTool):
    """
    A tool to retrieve relevant documents from a user-specific vector store.
    """
    name: str = "retrieve_course_material"
    description: str = (
        "Use this tool to retrieve relevant course material to answer a student's question. "
        "Provide a concise and targeted search query based on the student's latest question."
    )
    args_schema: Type[BaseModel] = RetrieveCourseMaterialInput

    def _run(self, *args, **kwargs):
        """This tool should not be run synchronously."""
        raise NotImplementedError("This tool does not support synchronous execution.")

    async def _arun(self, query: str, user_id: str) -> str:
        """
        Asynchronous execution of the tool.
        The `user_id` is injected by the agent, not provided by the LLM.
        """
        if not user_id:
            return "Error: User context is missing. Cannot perform retrieval."

        collection_name = f"user_{user_id}"
        
        # Get the retriever using our robust factory function
        retriever = vectordb.get_langchain_retriever(collection_name)

        if retriever is None:
            return "No learning materials found. Please upload documents first."

        print(f"Retrieving documents for user '{user_id}' with query: '{query}'")
        # Use the async method to get documents
        docs = await retriever.ainvoke(query)

        if not docs:
            return "No relevant course material found for that query."

        # Format the retrieved documents into a single, clean string for the LLM
        formatted_docs = "\n\n---\n\n".join(
            [f"Source {i+1}:\n{doc.page_content}" for i, doc in enumerate(docs)]
        )
        return f"Retrieved the following materials to answer the question:\n{formatted_docs}"