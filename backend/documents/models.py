from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID, uuid4
from typing import TYPE_CHECKING
from repositories.models import RepositoryDocumentLink


if TYPE_CHECKING:
    from repositories.models import Repository


class DocumentBase(SQLModel):
    title: str
    content: str
    source_file: str | None = None


class Document(DocumentBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    repositories: list["Repository"] = Relationship(
        back_populates="documents",
        link_model=RepositoryDocumentLink,
    )


class DocumentCreate(DocumentBase):
    pass


class DocumentPublic(DocumentBase):
    id: UUID
    title: str
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


# class ChunkTaskLink(SQLModel, table=True):
#     chunk_id: UUID | None = Field(
#         default=None, foreign_key="chunk.id", primary_key=True
#     )
#     task_id: UUID | None = Field(default=None, foreign_key="task.id", primary_key=True)
#     created_at: datetime = Field(default_factory=datetime.now)
#     deleted_at: datetime | None = None


class Chunk(ChunkBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None
    chunk_length: int

    # Relationships
    # tasks: list["Task"] = Relationship(
    #     back_populates="chunk",
    #     link_model=ChunkTaskLink,
    # )


class ChunkCreate(ChunkBase):
    chunk_length: int
