from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field


class ReportBase(SQLModel):
    """Base fields for user reports."""

    # free-form type, e.g. "generic" or "task"
    report_type: str = Field(default="generic")
    # page URL where the report was created
    url: str
    # optional comma-separated tags like: "too_easy,not_relevant"
    category_tags: Optional[str] = None
    # optional user-entered text
    message: Optional[str] = None
    # optional user agent string for debugging
    user_agent: Optional[str] = None
    # optional contextual references
    # If a referenced task or unit is deleted, keep the report and null the FK
    task_id: Optional[UUID] = Field(
        default=None, foreign_key="task.id", ondelete="SET NULL"
    )
    unit_id: Optional[UUID] = Field(
        default=None, foreign_key="unit.id", ondelete="SET NULL"
    )


class Report(ReportBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.now)


class ReportCreate(SQLModel):
    report_type: str = "generic"
    url: str
    category_tags: Optional[str] = None
    message: Optional[str] = None
    user_agent: Optional[str] = None
    task_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None


class ReportRead(SQLModel):
    id: UUID
    report_type: str
    url: str
    category_tags: Optional[str] = None
    message: Optional[str] = None
    user_agent: Optional[str] = None
    task_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    user_id: UUID
    created_at: datetime
