from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from tasks.models import Task


class DocumentBase(SQLModel):
    title: str
    content: str
    source_file: Optional[str] = None
    total_chunks: int = 0


class Document(DocumentBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    chunks: List["Chunk"] = Relationship(back_populates="document", cascade_delete=True)
    tasks: List["Task"] = Relationship(back_populates="document")


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: UUID
    created_at: datetime


class DocumentUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    source_file: Optional[str] = None
    total_chunks: Optional[int] = None


class DocumentDelete(SQLModel):
    pass


class DocumentDeleteResponse(SQLModel):
    message: str


class ChunkBase(SQLModel):
    document_id: UUID = Field(foreign_key="document.id")
    chunk_index: int
    chunk_text: str
    chunk_length: int


class Chunk(ChunkBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    document: Optional[Document] = Relationship(back_populates="chunks")
    tasks: List["Task"] = Relationship(back_populates="chunk")

    # Ensure unique combination of document_id and chunk_index
    __table_args__ = {"sqlite_autoincrement": True}


class ChunkCreate(ChunkBase):
    pass


class ChunkRead(ChunkBase):
    id: UUID
    created_at: datetime


class ChunkUpdate(SQLModel):
    chunk_text: Optional[str] = None
    chunk_length: Optional[int] = None
