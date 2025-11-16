from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from repositories.models import Repository
    from tasks.models import Task

class UnitTaskAction(str, Enum):
    ADDED = "added"
    REMOVED = "removed"

class UnitTaskLink(SQLModel, table=True):
    unit_id: UUID | None = Field(default=None, foreign_key="unit.id", primary_key=True)
    task_id: UUID | None = Field(default=None, foreign_key="task.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

class UnitTaskEvent(SQLModel, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    unit_id: UUID = Field(foreign_key="unit.id", index=True)
    task_id: UUID = Field(foreign_key="task.id", index=True)
    action: UnitTaskAction
    user_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class UnitBase(SQLModel):
    title: str
    content: str | None = None


class Unit(UnitBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None
    repository_id: UUID = Field(foreign_key="repository.id", ondelete="CASCADE")

    # Relationships
    repository: "Repository" = Relationship(back_populates="units")
    tasks: list["Task"] = Relationship(
        back_populates="units",
        link_model=UnitTaskLink,
    )


class UnitCreate(UnitBase):
    repository_id: UUID


class UnitUpdate(SQLModel):
    title: str | None = None
    content: str | None = None
    repository_id: UUID | None = None


class UnitResponse(UnitBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    repository_id: UUID
    task_count: int = 0


class UnitListResponse(SQLModel):
    id: UUID
    title: str
    created_at: datetime
    deleted_at: datetime | None = None
    repository_id: UUID
    task_count: int = 0


class UnitResponseDetail(UnitBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    repository_id: UUID
    repository_name: str
    task_ids: list[UUID] = []
    task_count: int = 0


class UnitDelete(SQLModel):
    pass
