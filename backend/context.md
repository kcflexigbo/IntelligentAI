# Context Generation Report

---

**Generation Timestamp:** `2025-10-30 12:31:31`

**Language Profile:** `Python`

**Configuration:**
- **Mode:** `Ignore`
- **Allowed Extensions:** `.py, .pyw, .pyi, .pyx, .cyp, .json, .yaml, .yml, .toml, .ini, .cfg`
- **Ignored Patterns:** `build, dist, *.egg-info, *.pyc, __pycache__, .tox, .pytest_cache`
- **Restricted Extensions:** `*.pyc, *.pyd, *.so`

---

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\api\endpoints\auth.py

```python
from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import models
from app.db.session import get_db
from app.schemas.auth import Token, UserCreate, UserResponse
from app.services import auth_service
from app.core.config import settings
router = APIRouter()
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    query = select(models.User).where(models.User.email == user_in.email)
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    hashed_password = auth_service.get_password_hash(user_in.password)
    new_user = models.User(email=user_in.email, hashed_password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
@router.post("/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    query = select(models.User).where(models.User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    try:
        auth_service.verify_password(form_data.password, user.hashed_password)
    except Exception as e:
        user = None
        print(f"Error during password verification: {e}")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\api\endpoints\chat.py

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from langchain_core.messages import HumanMessage, AIMessage
from app.db.session import get_db
from app.db import models # <-- Import models
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import agent_service
from app.services.auth_service import get_current_user
router = APIRouter()
@router.post("", response_model=ChatResponse)
async def get_chat_response(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user) # <-- Get current user
):
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        history_query = (
            select(models.ChatMessage)
            .where(models.ChatMessage.session_id == request.session_id)
            .where(models.ChatMessage.user_id == current_user.id)
            .order_by(models.ChatMessage.created_at)
        )
        result = await db.execute(history_query)
        db_messages = result.scalars().all()
        chat_history = [
            HumanMessage(content=msg.content) if msg.is_from_user else AIMessage(content=msg.content)
            for msg in db_messages
        ]
        final_state = await agent_service.invoke_agent(request.question, chat_history, db)
        user_message = models.ChatMessage(
            session_id=request.session_id,
            user_id=current_user.id,
            content=request.question,
            is_from_user=True
        )
        ai_answer = final_state.get("answer", "Sorry, I couldn't process your request.")
        ai_message = models.ChatMessage(
            session_id=request.session_id,
            user_id=current_user.id,
            content=ai_answer,
            is_from_user=False
        )
        db.add_all([user_message, ai_message])
        await db.commit()
        return ChatResponse(
            answer=ai_answer,
            retrieved_context=final_state.get("context", []),
            rewritten_question=final_state.get("rewritten_question")
        )
    except Exception as e:
        print(f"Error invoking agent: {e}")
        raise HTTPException(status_code=500, detail="Failed to get a response from the agent.")
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\api\endpoints\documents.py

```python
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db import models
from app.schemas.document import DocumentResponse
from app.services import rag_service
from sqlalchemy import select
from app.services.auth_service import get_current_user
router = APIRouter()
@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint to upload a document.
    It creates a document record and triggers the background processing.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    document = models.Document(
        filename=file.filename,
        user_id=current_user.id
    )
    db.add(document)
    await db.commit()
    await db.refresh(document) # Refresh to get the auto-generated ID
    document_id = document.id
    await rag_service.process_and_embed_document(
        db=db,
        document_record=document,
        file_content=file_content,
        filename=file.filename
    )
    result = await db.execute(select(models.Document).where(models.Document.id == document_id))
    refreshed_document = result.scalar_one()
    response_data = DocumentResponse(
        id=refreshed_document.id,
        filename=refreshed_document.filename,
        uploaded_at=refreshed_document.uploaded_at,
        user_id=refreshed_document.user_id
    )
    return response_data
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\core\config.py

```python
import os
from dotenv import load_dotenv
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")
class Settings:
    """
    Application settings loaded from environment variables.
    """
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    EMBEDDING_DIM: int = 384
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "DEFAULT_KEY")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_default_secret_key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
settings = Settings()
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\db\base.py

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\db\models.py

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    func
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.db.session import Base
from app.core.config import settings
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    owner = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    document = relationship("Document", back_populates="chunks")
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False) # To group conversations
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_from_user = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # Use server timestamp
    user = relationship("User", back_populates="chat_messages")
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\db\session.py

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings
engine = create_async_engine(settings.DATABASE_URL, echo=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False  # Good practice for async sessions
)
Base = declarative_base()
async def get_db() -> AsyncSession:
    """
    FastAPI dependency that provides a database session per request.
    """
    async with AsyncSessionLocal() as session:
        yield session
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\main.py

```python
from fastapi import FastAPI
from app.api.endpoints import documents
from app.api.endpoints import chat
from app.api.endpoints import auth
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="Intelligent Learning Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
@app.get("/")
def read_root():
    return {"message": "Welcome to the Intelligent Learning Assistant API"}
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\schemas\auth.py

```python
from pydantic import BaseModel, ConfigDict, EmailStr
class UserCreate(BaseModel):
    email: EmailStr
    password: str
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)
class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    email: str | None = None
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\schemas\chat.py

```python
from pydantic import BaseModel
from typing import List, Optional 
class ChatRequest(BaseModel):
    """
    Schema for an incoming chat question.
    """
    question: str
    session_id: str  # To track conversation history later
class ChatResponse(BaseModel):
    """
    Schema for the response from the chat agent.
    """
    answer: str
    retrieved_context: List[str]
    rewritten_question: Optional[str] = None
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\schemas\document.py

```python
from pydantic import BaseModel, ConfigDict
from datetime import datetime
class DocumentResponse(BaseModel):
    """
    Pydantic schema for the response after a document is uploaded.
    """
    id: int
    filename: str
    uploaded_at: datetime
    user_id: int
    model_config = ConfigDict(from_attributes=True)
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\services\agent_service.py

```python
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
    async def grade_single_doc(doc):
        result = await grading_chain.ainvoke({"question": question, "document": doc.content})
        is_relevant = result.binary_score.lower() == "yes"
        if is_relevant:
            print(f"---Document ID {doc.id} is RELEVANT---")
        else:
            print(f"---Document ID {doc.id} is NOT RELEVANT---")
        return (doc, is_relevant)
    import asyncio
    grading_results = await asyncio.gather(*[grade_single_doc(doc) for doc in documents_to_grade])
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
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\services\auth_service.py

```python
from datetime import datetime, timedelta, timezone
from typing import Annotated
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.config import settings
from app.db import models
from app.db.session import get_db
from app.schemas.auth import TokenData
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    query = select(models.User).where(models.User.email == token_data.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\services\rag_service.py

```python
import os
from tempfile import NamedTemporaryFile
from typing import List
from langchain_community.document_loaders import PyPDFLoader
import warnings
from langchain_unstructured import UnstructuredLoader as UnstructuredFileLoader  # type: ignore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import models
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,  # The size of each chunk in characters
    chunk_overlap=100, # The number of characters to overlap between chunks
)
async def process_and_embed_document(
    db: AsyncSession,
    document_record: models.Document,
    file_content: bytes,
    filename: str
):
    """
    Processes an uploaded file, chunks it, creates embeddings, and stores them.
    Args:
        db: The database session.
        document_record: The SQLAlchemy Document model instance.
        file_content: The raw content of the file.
        filename: The name of the file to determine the loader.
    """
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    try:
        if filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(tmp_path)
        else:
            loader = UnstructuredFileLoader(tmp_path)
        docs = loader.load()
        chunks = text_splitter.split_documents(docs)
        if not chunks:
            print("Warning: Document could not be split into chunks.")
            return
        db_chunks: List[models.DocumentChunk] = []
        chunk_texts = [chunk.page_content for chunk in chunks]
        chunk_embeddings = embeddings.embed_documents(chunk_texts)
        for i, chunk in enumerate(chunks):
            db_chunks.append(
                models.DocumentChunk(
                    document_id=document_record.id,
                    content=chunk.page_content,
                    embedding=chunk_embeddings[i]
                )
            )
        db.add_all(db_chunks)
        await db.commit()
        print(f"Successfully processed and stored {len(db_chunks)} chunks for document: {filename}")
    finally:
        os.remove(tmp_path)
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\tests\conftest.py

```python
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
from app.services import auth_service
url = settings.DATABASE_URL
if not url.find("learning_assistant_test") != -1:
    url = url.replace("learning_assistant", "learning_assistant_test")
TEST_DATABASE_URL = url
@pytest.fixture(scope="function")
async def db_engine():
    """
    Fixture to create and manage the database engine per test function.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=True, poolclass=None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
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
    transport = ASGITransport(app=main_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
@pytest.fixture(scope="function")
async def authenticated_client(
    client: AsyncClient, db_session: AsyncSession
) -> AsyncClient:
    """
    Fixture to create an authenticated client.
    It registers and logs in a test user, then sets the
    authorization header on the client for subsequent requests.
    """
    user_data = {"email": "test@example.com", "password": "testpassword"}
    await client.post("/auth/register", json=user_data)
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"],
    }
    response = await client.post("/auth/login", data=login_data)
    token = response.json()["access_token"]
    client.headers = {
        "Authorization": f"Bearer {token}",
    }
    return client
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\tests\test_chat_endpoint.py

```python
import pytest
from unittest.mock import AsyncMock, call
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import models
from app.services import agent_service
from app.services.rag_service import embeddings
from langchain_core.messages import HumanMessage, AIMessage # <-- Import message types
pytestmark = pytest.mark.asyncio
async def test_chat_endpoint_retrieves_and_generates(
    authenticated_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests the full RAG flow from the /chat endpoint.
    - Seeds the database with a specific document chunk.
    - Mocks the LLM call to return a predictable response.
    - Verifies that the correct context is retrieved and a valid answer is returned.
    """
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    test_doc = models.Document(id=1, filename="test.txt", user_id=test_user.id)
    db_session.add(test_doc)
    await db_session.commit()
    chunk_content = "LangGraph is a library for building stateful, multi-actor applications with LLMs."
    chunk_embedding = embeddings.embed_query(chunk_content) # Use the real embedding model
    test_chunk = models.DocumentChunk(
        document_id=1,
        content=chunk_content,
        embedding=chunk_embedding
    )
    db_session.add(test_chunk)
    await db_session.commit()
    mock_answer = agent_service.RAGAnswer(
        answer="LangGraph is a tool for creating agentic applications using LLMs."
    )
    mock_rag_chain_ainvoke = AsyncMock(return_value=mock_answer)
    mock_chain = AsyncMock()
    mock_chain.ainvoke = mock_rag_chain_ainvoke
    monkeypatch.setattr(agent_service, "rag_chain", mock_chain)
    user_question = "What is LangGraph?"
    request_data = {"question": user_question, "session_id": "test_session_1"}
    response = await authenticated_client.post("/chat", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == mock_answer.answer
    assert len(data["retrieved_context"]) > 0
    assert data["retrieved_context"][0] == chunk_content
    mock_rag_chain_ainvoke.assert_called_once()
    call_args, _ = mock_rag_chain_ainvoke.call_args
    passed_context = call_args[0]["context"]
    assert chunk_content in passed_context
    assert call_args[0]["question"] == user_question
async def test_chat_with_history_rewrites_question(
    authenticated_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests that the agent uses chat history to rewrite a follow-up question.
    """
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    session_id = "test_conversation_123"
    test_doc = models.Document(id=1, filename="test.txt", user_id=test_user.id)
    db_session.add(test_doc)
    prior_user_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="What is LangGraph?", is_from_user=True
    )
    prior_ai_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="It is a library for building agents.", is_from_user=False
    )
    db_session.add_all([test_user, test_doc])
    prior_user_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="What is LangGraph?", is_from_user=True
    )
    prior_ai_msg = models.ChatMessage(
        session_id=session_id, user_id=test_user.id, content="It is a library for building agents.", is_from_user=False
    )
    db_session.add_all([prior_user_msg, prior_ai_msg])
    await db_session.commit()
    chunk_content = "LangGraph is primarily used for creating cyclical graphs for agent runtimes."
    chunk_embedding = embeddings.embed_query(chunk_content)
    test_chunk = models.DocumentChunk(
        document_id=1, content=chunk_content, embedding=chunk_embedding
    )
    db_session.add(test_chunk)
    await db_session.commit()
    rewritten_question = "What is LangGraph used for?"
    mock_rewriter_answer = agent_service.RewrittenQuestion(
        rewritten_question=rewritten_question
    )
    mock_rewriter_chain_ainvoke = AsyncMock(return_value=mock_rewriter_answer)
    mock_rewriter_chain = AsyncMock()
    mock_rewriter_chain.ainvoke = mock_rewriter_chain_ainvoke
    monkeypatch.setattr(agent_service, "rewriter_chain", mock_rewriter_chain)
    final_answer = "LangGraph is used for creating agent runtimes."
    mock_rag_answer = agent_service.RAGAnswer(answer=final_answer)
    mock_rag_chain_ainvoke = AsyncMock(return_value=mock_rag_answer)
    mock_rag_chain = AsyncMock()
    mock_rag_chain.ainvoke = mock_rag_chain_ainvoke
    monkeypatch.setattr(agent_service, "rag_chain", mock_rag_chain)
    follow_up_question = "what is it used for?"
    response = await authenticated_client.post(
        "/chat",
        json={"question": follow_up_question, "session_id": session_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == final_answer
    assert data["rewritten_question"] == rewritten_question
    mock_rewriter_chain_ainvoke.assert_called_once()
    rewriter_call_args = mock_rewriter_chain_ainvoke.call_args[0][0]
    assert rewriter_call_args["question"] == follow_up_question
    assert len(rewriter_call_args["chat_history"]) == 2
    assert rewriter_call_args["chat_history"][0].content == "What is LangGraph?"
    mock_rag_chain_ainvoke.assert_called_once()
    rag_call_args = mock_rag_chain_ainvoke.call_args[0][0]
    assert rag_call_args["question"] == follow_up_question # Uses original question for final answer
    assert chunk_content in rag_call_args["context"]
    result = await db_session.execute(
        select(models.ChatMessage)
        .where(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.created_at)
    )
    all_messages = result.scalars().all()
    assert len(all_messages) == 4 # 2 old messages + 2 new ones
    assert all_messages[2].content == follow_up_question
    assert all_messages[2].is_from_user is True
    assert all_messages[3].content == final_answer
    assert all_messages[3].is_from_user is False
async def test_chat_with_reranking_filters_documents(
    authenticated_client: AsyncClient, db_session: AsyncSession, monkeypatch
):
    """
    Tests that the grading and re-ranking step correctly filters out
    irrelevant documents before the final generation.
    """
    session_id = "test_reranking_session"
    user_question = "What is the purpose of LangGraph?"
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    session_id = "test_reranking_session"
    test_doc = models.Document(id=1, filename="test.txt", user_id=test_user.id)
    db_session.add(test_doc)
    await db_session.commit()
    relevant_content = "LangGraph is a library for building stateful, multi-actor applications with LLMs, used for agentic architectures."
    relevant_embedding = embeddings.embed_query(relevant_content)
    relevant_chunk = models.DocumentChunk(
        document_id=1, content=relevant_content, embedding=relevant_embedding
    )
    irrelevant_content = "Graph theory is the study of mathematical structures used to model pairwise relations between objects."
    irrelevant_embedding = embeddings.embed_query(irrelevant_content)
    irrelevant_chunk = models.DocumentChunk(
        document_id=1, content=irrelevant_content, embedding=irrelevant_embedding
    )
    db_session.add_all([relevant_chunk, irrelevant_chunk])
    await db_session.commit()
    mock_rewriter_ainvoke = AsyncMock(
        return_value=agent_service.RewrittenQuestion(rewritten_question=user_question)
    )
    mock_rewriter_chain = AsyncMock()
    mock_rewriter_chain.ainvoke = mock_rewriter_ainvoke
    monkeypatch.setattr(agent_service, "rewriter_chain", mock_rewriter_chain)
    async def grading_side_effect(inputs):
        doc_content = inputs["document"]
        if "LangGraph" in doc_content:
            return agent_service.GradeDocuments(binary_score="yes")
        else:
            return agent_service.GradeDocuments(binary_score="no")
    mock_grading_ainvoke = AsyncMock(side_effect=grading_side_effect)
    mock_grading_chain = AsyncMock()
    mock_grading_chain.ainvoke = mock_grading_ainvoke
    monkeypatch.setattr(agent_service, "grading_chain", mock_grading_chain)
    final_answer = "LangGraph is for building agentic applications."
    mock_rag_ainvoke = AsyncMock(
        return_value=agent_service.RAGAnswer(answer=final_answer)
    )
    mock_rag_chain = AsyncMock()
    mock_rag_chain.ainvoke = mock_rag_ainvoke
    monkeypatch.setattr(agent_service, "rag_chain", mock_rag_chain)
    response = await authenticated_client.post(
        "/chat",
        json={"question": user_question, "session_id": session_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == final_answer
    assert mock_grading_ainvoke.call_count == 2
    mock_rag_ainvoke.assert_called_once()
    rag_call_args = mock_rag_ainvoke.call_args[0][0]
    final_context = rag_call_args["context"]
    assert relevant_content in final_context
    assert irrelevant_content not in final_context
    result = await db_session.execute(
        select(models.ChatMessage).where(models.ChatMessage.session_id == session_id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2
    assert messages[1].content == final_answer
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\tests\test_document_upload.py

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db import models
pytestmark = pytest.mark.asyncio
async def test_upload_document_and_process(
    authenticated_client: AsyncClient, db_session: AsyncSession
):
    """
    Tests the entire document upload and processing flow.
    """
    res = await db_session.execute(select(models.User).where(models.User.email == "test@example.com"))
    test_user = res.scalar_one()
    user_id = test_user.id
    dummy_file_content = "This is a test document for the learning assistant."
    files = {"file": ("test_doc.txt", dummy_file_content, "text/plain")}
    response = await authenticated_client.post("/documents/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test_doc.txt"
    assert data["user_id"] == user_id
    document_id = data["id"]
    doc_result = await db_session.execute(
        select(models.Document).where(models.Document.id == document_id)
    )
    doc_in_db = doc_result.scalar_one_or_none()
    assert doc_in_db is not None
    assert doc_in_db.filename == "test_doc.txt"
    chunk_result = await db_session.execute(
        select(models.DocumentChunk).where(models.DocumentChunk.document_id == document_id)
    )
    chunks_in_db = chunk_result.scalars().all()
    assert len(chunks_in_db) == 1
    first_chunk = chunks_in_db[0]
    assert first_chunk.content == dummy_file_content
    assert first_chunk.embedding is not None
    assert len(first_chunk.embedding) == 384
```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\app\__init__.py

```python

```

## FILE: C:/Users/ROG/Documents/Codes/IntelligentAI/backend\pytest.ini

```
[pytest]
testpaths = app/tests
pythonpath = .
asyncio_mode = auto
```

