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
    Table,  # Import Table
    func,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.db.session import Base
from app.core.config import settings
import enum


class FileType(str, enum.Enum):
    """Enum for document file types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"

# Association Table for the many-to-many relationship
conversation_document_link = Table(
    'conversation_document_link',
    Base.metadata,
    Column('conversation_id', Integer, ForeignKey('conversations.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class Course(Base):
    """Model for courses that have pre-loaded materials."""
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    documents = relationship("Document", back_populates="course", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for course materials
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Media-related fields
    file_type = Column(SQLEnum(FileType, native_enum=False), nullable=False, default=FileType.TEXT)
    s3_key = Column(String, nullable=True)  # Path in MinIO/S3
    transcription = Column(Text, nullable=True)  # For video transcripts or OCR text
    
    # Course material fields
    is_course_material = Column(Boolean, default=False, nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)

    owner = relationship("User", back_populates="documents")
    course = relationship("Course", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Relationship to conversations through the association table
    conversations = relationship(
        "Conversation",
        secondary=conversation_document_link,
        back_populates="documents"
    )

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    
    document = relationship("Document", back_populates="chunks")

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, default="New Conversation")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    # Relationship to documents through the association table
    documents = relationship(
        "Document",
        secondary=conversation_document_link,
        back_populates="conversations",
        cascade="all, delete"  # Ensures link is deleted when a conversation is deleted
    )

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_from_user = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    conversation = relationship("Conversation", back_populates="messages")