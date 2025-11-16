from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING
from enum import Enum

# Import link models to avoid string reference issues
from tasks.stats import TaskStatistics

if TYPE_CHECKING:
    from documents.models import Document
    from units.models import Unit
    from auth.models import User
    from skills.models import Skill, RepositorySkillLink


class AccessLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    OWNER = "owner"


class RepositoryAccess(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    repository_id: UUID = Field(foreign_key="repository.id")
    access_level: AccessLevel = Field(default=AccessLevel.READ)
    granted_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    user: "User" = Relationship(back_populates="repository_access")
    repository: "Repository" = Relationship(back_populates="user_access")


class RepositoryAccessCreate(SQLModel):
    user_id: UUID
    repository_id: UUID
    access_level: AccessLevel = AccessLevel.READ


class RepositoryAccessUpdate(SQLModel):
    access_level: AccessLevel


class RepositoryAccessResponse(SQLModel):
    id: UUID
    user_id: UUID
    repository_id: UUID
    access_level: AccessLevel
    granted_at: datetime


class RepositoryBase(SQLModel):
    name: str = Field(..., min_length=1, description="Repository name cannot be empty")


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
    owner_id: UUID | None = Field(default=None, foreign_key="user.id")

    # Relationships
    documents: list["Document"] = Relationship(
        back_populates="repositories",
        sa_relationship_kwargs={"secondary": "repositorydocumentlink"}
    )
    units: list["Unit"] = Relationship(
        back_populates="repository",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    skills: list["Skill"] = Relationship(
        back_populates="repositories",
        sa_relationship_kwargs={"secondary": "repositoryskilllink"}
    )
    user_access: list["RepositoryAccess"] = Relationship(back_populates="repository")
    task_statistics: list["TaskStatistics"] = Relationship(back_populates="repository")


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryUpdate(SQLModel):
    name: str = Field(..., min_length=1, description="Repository name cannot be empty")


class RepositoryResponse(RepositoryBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    unit_count: int = 0
    skill_count: int = 0
    access_level: AccessLevel = AccessLevel.READ


class RepositoryResponseDetail(RepositoryBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    access_level: AccessLevel = AccessLevel.READ
    document_ids: list[UUID] = []
    document_names: list[str] = []
    unit_ids: list[UUID] = []
    unit_names: list[str] = []
    skill_ids: list[UUID] = []
    skill_names: list[str] = []


class RepositoryDocumentLinkCreate(SQLModel):
    repository_id: UUID
    document_id: UUID


class RepositoryDocumentLinkResponse(SQLModel):
    repository_id: UUID
    document_id: UUID
    created_at: datetime


class RepositoryAccessGrantByEmail(SQLModel):
    email: str
    access_level: AccessLevel = AccessLevel.READ


class RepositoryUserResponse(SQLModel):
    """Response model for users with repository access"""

    user_id: UUID
    email: str | None
    full_name: str | None
    access_level: AccessLevel
    granted_at: datetime
    is_owner: bool = False
