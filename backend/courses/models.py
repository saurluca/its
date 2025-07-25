from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4


class CourseBase(SQLModel):
    name: str


class Course(CourseBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships - using forward reference to avoid circular imports
    tasks: List["Task"] = Relationship(back_populates="course")


class CourseCreate(CourseBase):
    pass


class CourseRead(CourseBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class CourseUpdate(SQLModel):
    name: Optional[str] = None
