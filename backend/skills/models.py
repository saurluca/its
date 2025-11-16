from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime

from tasks.versions import TaskVersion
if TYPE_CHECKING:
    from tasks.models import Task
    from repositories.models import Repository
    from auth.models import User


# many to many skill to user with progress tracking
class UserSkillLink(SQLModel, table=True):
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    skill_id: UUID = Field(foreign_key="skill.id", primary_key=True)
    progress: float = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


# many to many repository to skill
class RepositorySkillLink(SQLModel, table=True):
    repository_id: UUID = Field(foreign_key="repository.id", primary_key=True)
    skill_id: UUID = Field(foreign_key="skill.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


class SkillBase(SQLModel):
    name: str = Field(unique=True, index=True)


class Skill(SkillBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    # to track progress of users on this skill
    users: list["User"] = Relationship(
        back_populates="skills",
        link_model=UserSkillLink,
    )
    # to determine which repos have this skill
    repositories: list["Repository"] = Relationship(
        back_populates="skills",
        link_model=RepositorySkillLink,
    )
    # to determine which tasks are associated with this skill
    tasks: list["Task"] = Relationship(
        back_populates="skill",
    )
    task_versions: list["TaskVersion"] = Relationship(back_populates="skill")


# Pydantic models for API operations
class SkillCreate(SkillBase):
    pass


class SkillUpdate(SQLModel):
    name: str | None = None


class SkillRead(SkillBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None


class UserSkillProgress(SQLModel):
    skill_id: UUID
    skill_name: str
    progress: float
    updated_at: datetime
