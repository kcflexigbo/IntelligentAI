import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

class Settings:
    """
    Application settings loaded from environment variables.
    """
    # Note: The DATABASE_URL must start with "postgresql+asyncpg://"
    # for SQLAlchemy's async support with asyncpg.
    # Example: postgresql+asyncpg://user:password@localhost:5432/learning_assistant
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # Embedding model configuration
    # We are using all-MiniLM-L6-v2, which has 384 dimensions.
    EMBEDDING_DIM: int = 384

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "DEFAULT_KEY")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

settings = Settings()