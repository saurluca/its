from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
import json


# Import the new models


class DocumentBase(SQLModel):
    title: str
    content: str
    key_points: Optional[str] = None
    source_file: Optional[str] = None
    total_chunks: int = 0


class Document(DocumentBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    chunks: List["Chunk"] = Relationship(back_populates="document", cascade_delete=True)
    questions: List["Question"] = Relationship(back_populates="document")


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: UUID
    created_at: datetime


class DocumentUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    key_points: Optional[str] = None
    source_file: Optional[str] = None
    total_chunks: Optional[int] = None


class ChunkBase(SQLModel):
    document_id: UUID = Field(foreign_key="document.id")
    chunk_index: int
    chunk_text: str
    chunk_metadata: Optional[str] = None  # JSON string


class Chunk(ChunkBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # embedding: Optional[List[float]] = None  # For vector embeddings, needs special handling

    # Relationships
    document: Optional[Document] = Relationship(back_populates="chunks")

    # Ensure unique combination of document_id and chunk_index
    __table_args__ = {"sqlite_autoincrement": True}

    def get_metadata_dict(self) -> dict:
        """Convert chunk_metadata JSON string to dictionary"""
        if self.chunk_metadata:
            try:
                return json.loads(self.chunk_metadata)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_metadata_dict(self, metadata_dict: dict):
        """Convert dictionary to chunk_metadata JSON string"""
        self.chunk_metadata = json.dumps(metadata_dict)


class ChunkCreate(ChunkBase):
    pass


class ChunkRead(ChunkBase):
    id: UUID
    created_at: datetime


class QuestionBase(SQLModel):
    question: str
    answer_options: str  # JSON string representation of list
    document_id: UUID = Field(foreign_key="document.id")


class Question(QuestionBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    # Relationships
    document: Optional[Document] = Relationship(back_populates="questions")

    def get_answer_options_list(self) -> List[str]:
        """Convert answer_options JSON string to list"""
        try:
            return json.loads(self.answer_options)
        except json.JSONDecodeError:
            return []

    def set_answer_options_list(self, options: List[str]):
        """Convert list to answer_options JSON string"""
        self.answer_options = json.dumps(options)


class QuestionCreate(QuestionBase):
    pass


class QuestionRead(QuestionBase):
    id: UUID
