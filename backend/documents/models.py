from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from repositories.models import RepositoryDocumentLink


if TYPE_CHECKING:
    from repositories.models import Repository
    from tasks.models import Task


class DocumentBase(SQLModel):
    title: str
    content: str
    source_file: str | None = None


class Document(DocumentBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    chunks: list["Chunk"] = Relationship(
        back_populates="document",
        cascade_delete=True,
    )

    repositories: list["Repository"] = Relationship(
        back_populates="documents",
        link_model=RepositoryDocumentLink,
    )


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    repository_ids: list[UUID] = []


class DocumentUpdate(SQLModel):
    title: str | None = None
    content: str | None = None
    source_file: str | None = None
    total_chunks: int | None = None


class DocumentDelete(SQLModel):
    pass


class ChunkBase(SQLModel):
    chunk_index: int
    chunk_text: str


class Chunk(ChunkBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None
    chunk_length: int

    # Relationships
    document_id: UUID = Field(foreign_key="document.id")
    document: Document = Relationship(back_populates="chunks")
    tasks: list["Task"] = Relationship(
        back_populates="chunk",
        cascade_delete=True,
    )


class ChunkCreate(ChunkBase):
    chunk_length: int
