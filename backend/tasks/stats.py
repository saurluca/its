# tasks/stats.py

from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repositories.models import Repository


class TaskStatistics(SQLModel, table=True):
    """
    One statistics row per repository.
    Tracks counts of created/deleted/modified tasks.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    repository_id: UUID = Field(
        foreign_key="repository.id",
        unique=True,
        index=True
    )

    total_created: int = Field(default=0)
    total_deleted: int = Field(default=0)  # Requirement #4
    total_modified: int = Field(default=0)  # Requirement #5

    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    repository: "Repository" = Relationship(back_populates="task_statistics")
