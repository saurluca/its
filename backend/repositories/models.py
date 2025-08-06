from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from documents.models import Document


class RepositoryBase(SQLModel):
    name: str


class RepositoryDocumentLink(SQLModel, table=True):
    repository_id: UUID | None = Field(
        default=None, foreign_key="repository.id", primary_key=True
    )
    document_id: UUID | None = Field(
        default=None, foreign_key="document.id", primary_key=True
    )
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


class Repository(RepositoryBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    documents: list["Document"] = Relationship(
        back_populates="repositories",
        link_model=RepositoryDocumentLink,
    )


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryUpdate(SQLModel):
    name: str


class RepositoryResponse(RepositoryBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None


class RepositoryResponseDetail(RepositoryBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    document_ids: list[UUID] = []
    document_names: list[str] = []


class RepositoryDocumentLinkCreate(SQLModel):
    repository_id: UUID
    document_id: UUID


class RepositoryDocumentLinkResponse(SQLModel):
    repository_id: UUID
    document_id: UUID
    created_at: datetime
