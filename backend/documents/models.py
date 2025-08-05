from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from repositories.models import Repository, RepositoryDocumentLink

if TYPE_CHECKING:
    from tasks.models import Task


class DocumentBase(SQLModel):
    title: str
    content: str
    source_file: str | None = None


class Document(DocumentBase, table=True):
    id: UUID | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    chunks: list["Chunk"] = Relationship(
        back_populates="documents", cascade_delete=True
    )
    repositories: list["Repository"] = Relationship(
        back_populates="documents",
        link_model=RepositoryDocumentLink,
    )


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: UUID
    created_at: datetime


class DocumentUpdate(SQLModel):
    title: str | None = None
    content: str | None = None
    source_file: str | None = None
    total_chunks: int | None = None


class DocumentDelete(SQLModel):
    pass


class ChunkBase(SQLModel):
    document_id: UUID | None = Field(default=None, foreign_key="document.id")
    chunk_index: int
    chunk_text: str


class ChunkTaskLink(SQLModel, table=True):
    chunk_id: UUID | None = Field(
        default=None, foreign_key="chunk.id", primary_key=True
    )
    task_id: UUID | None = Field(default=None, foreign_key="task.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


class Chunk(ChunkBase, table=True):
    id: UUID | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None
    chunk_length: int

    # Relationships
    document: Document | None = Relationship(back_populates="chunks")
    tasks: list["Task"] = Relationship(
        back_populates="chunk",
        link_model=ChunkTaskLink,
    )


class ChunkCreate(ChunkBase):
    chunk_length: int


class ChunkRead(ChunkBase):
    id: UUID
    created_at: datetime


class ChunkUpdate(SQLModel):
    chunk_text: str | None = None
    chunk_length: int | None = None


class ChunkDelete(SQLModel):
    pass
