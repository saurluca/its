# analytics/models.py
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from auth.models import User


class PageType(str, Enum):
    TASKS = "tasks"
    DOCUMENTS = "documents"
    SKILLS = "skills"
    REPOSITORIES = "repositories"
    HOME = "home"


class UserPageSession(SQLModel, table=True):
    """
    Tracks time spent on specific frontend pages.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="user.id", index=True)
    page: PageType

    entered_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    left_at: datetime | None = None

    duration_seconds: int | None = None
    
    # Relationships
    user: "User" = Relationship(back_populates="page_sessions")
