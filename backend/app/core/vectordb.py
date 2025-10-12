import chromadb
from chromadb.utils import embedding_functions
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Constants ---
# Use constants for easier configuration management
CHROMA_DB_PATH = "./chroma_db_persistent"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2" # A good, lightweight default for local dev

# --- Singleton Resource Management ---
# These heavy objects are initialized once when the module is first imported
# and reused across the application, saving memory and startup time.

# 1. Initialize the ChromaDB client with persistence
print("Initializing ChromaDB client...")
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# 2. Use Chroma's built-in embedding function utility for efficiency
# This is often faster and more tightly integrated than the LangChain community wrapper.
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL_NAME
)
print("Embedding function loaded.")

# 3. Initialize a text splitter for document processing
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# --- VectorDB Functions ---

def process_and_store_docs(documents: list[Document], collection_name: str) -> None:
    """
    Chunks documents, creates embeddings, and stores them in a specific ChromaDB collection.
    This function is idempotent: it gets or creates the collection.
    """
    print(f"Processing {len(documents)} documents for collection '{collection_name}'...")
    
    # Get or create the collection with the specified embedding function
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=sentence_transformer_ef
    )
    
    chunks = text_splitter.split_documents(documents)
    
    # Prepare documents for ChromaDB (content and metadata)
    chunk_contents = [chunk.page_content for chunk in chunks]
    chunk_metadatas = [chunk.metadata for chunk in chunks]
    chunk_ids = [f"{collection_name}_{i}" for i in range(len(chunks))]
    
    # Add the documents to the collection. `add` is an upsert operation.
    collection.add(
        ids=chunk_ids,
        documents=chunk_contents,
        metadatas=chunk_metadatas
    )
    print(f"Successfully added {len(chunks)} chunks to collection '{collection_name}'.")


def get_langchain_retriever(collection_name: str, k: int = 5):
    """
    Creates a LangChain-compatible retriever for a specific user's collection.
    This is the robust bridge between our ChromaDB client and LangChain.
    """
    # First, verify the collection actually exists to prevent runtime errors.
    try:
        client.get_collection(name=collection_name, embedding_function=sentence_transformer_ef)
    except ValueError:
        # This error is raised by ChromaDB if the collection doesn't exist.
        print(f"Warning: Collection '{collection_name}' does not exist. Retrieval will return no results.")
        return None

    # Create a LangChain Chroma wrapper pointing to the *existing* client and collection
    vector_store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=None, # The collection is already configured with an embedding function
    )
    
    return vector_store.as_retriever(search_kwargs={"k": k})