from sqlmodel import SQLModel, Field, Relationship, Index
from datetime import datetime
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repositories.models import Repository, RepositoryDocumentLink
    from tasks.models import Task
    from tasks.versions import TaskVersion


class DocumentBase(SQLModel):
    title: str
    content: str
    source_file: str | None = None


class Document(DocumentBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None
    summary: str | None = None

    # Relationships
    chunks: list["Chunk"] = Relationship(
        back_populates="document",
        cascade_delete=True,
    )

    repositories: list["Repository"] = Relationship(
        back_populates="documents",
        sa_relationship_kwargs={"secondary": "repositorydocumentlink"}
    )


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    repository_ids: list[UUID] = []


class DocumentListResponse(SQLModel):
    id: UUID
    title: str
    source_file: str | None = None
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
    important: bool = True

    # Relationships
    document_id: UUID = Field(foreign_key="document.id")
    document: Document = Relationship(back_populates="chunks")
    tasks: list["Task"] = Relationship(
        back_populates="chunk",
        cascade_delete=True,
    )
    task_versions: list["TaskVersion"] = Relationship(back_populates="chunk")


class ChunkCreate(ChunkBase):
    chunk_length: int
