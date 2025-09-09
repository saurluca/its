from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime

from repositories.models import RepositoryUnitLink


if TYPE_CHECKING:
    from repositories.models import Repository
    from tasks.models import Task


class UnitTaskLink(SQLModel, table=True):
    unit_id: UUID | None = Field(default=None, foreign_key="unit.id", primary_key=True)
    task_id: UUID | None = Field(default=None, foreign_key="task.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


class UnitBase(SQLModel):
    title: str
    content: str | None = None


class Unit(UnitBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    repositories: list["Repository"] = Relationship(
        back_populates="units",
        link_model=RepositoryUnitLink,
    )
    tasks: list["Task"] = Relationship(
        back_populates="units",
        cascade_delete=True,
    )
