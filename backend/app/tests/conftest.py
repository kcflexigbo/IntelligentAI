import asyncio
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.session import Base, get_db
from app.main import app as main_app # Import your main app
from app.core.config import settings

# --- 1. SETUP TEST DATABASE ---
url = settings.DATABASE_URL
if not url.find("learning_assistant_test") != -1:
    url = url.replace("learning_assistant", "learning_assistant_test")
TEST_DATABASE_URL = url

# --- 2. PYTEST FIXTURES ---

@pytest.fixture(scope="function")
async def db_engine():
    """
    Fixture to create and manage the database engine per test function.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=True, poolclass=None)
    
    async with engine.begin() as conn:
        # Make sure to create the vector extension
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Teardown: drop all tables after test is done
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture to provide a database session per test function.
    """
    TestingSessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture to create an AsyncClient for making API requests to the app.
    It overrides the `get_db` dependency to use the test database session.
    """
    def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    main_app.dependency_overrides[get_db] = override_get_db
    
    # --- THIS IS THE FIX ---
    # Instead of passing `app=main_app`, we create an ASGITransport
    # and pass that to the `transport` argument.
    transport = ASGITransport(app=main_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c