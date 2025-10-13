from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Create an asynchronous engine
# The engine is the starting point for any SQLAlchemy application.
# `echo=True` is useful for debugging as it logs all SQL statements.
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Create a configured "Session" class
# This is our session factory. We will call this to get a new session.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Good practice for async sessions
)

# Base class for our models
# All our database models will inherit from this class.
Base = declarative_base()

# Dependency to get a DB session in FastAPI endpoints
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a database session per request.
    """
    async with AsyncSessionLocal() as session:
        yield session