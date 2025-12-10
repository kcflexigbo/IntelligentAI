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
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # Embedding model configuration
    # We are using all-MiniLM-L6-v2, which has 384 dimensions.
    EMBEDDING_DIM: int = 384

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "DEFAULT_KEY")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_default_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3600 # 1 hour

    # MinIO/S3 Configuration
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "local-s3:9000")  # Internal endpoint for backend
    MINIO_EXTERNAL_ENDPOINT: str = os.getenv("MINIO_EXTERNAL_ENDPOINT", "localhost:9000")  # External endpoint for frontend
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "kenneth")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "kenneth2620")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "intelliteach")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() == "true"

settings = Settings()