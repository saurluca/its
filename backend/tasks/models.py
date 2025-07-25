from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import json
from courses.models import Course
from documents.models import Document


class TaskType(str, Enum):
    TRUE_FALSE = "true_false"
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"


class TaskBase(SQLModel):
    type: TaskType
    question: str
    options_json: Optional[str] = None
    correct_answer: str
    course_id: Optional[UUID] = None
    document_id: Optional[UUID] = Field(
        None, description="Document task was created from", foreign_key="document.id"
    )
    chunk_id: Optional[UUID] = Field(
        None, description="Chunk task was created from", foreign_key="chunk.id"
    )


class Task(TaskBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    course: Optional["Course"] = Relationship(back_populates="tasks")
    document: Optional["Document"] = Relationship(back_populates="tasks")

    def get_options_list(self) -> List[str]:
        """Convert options_json string to list"""
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except json.JSONDecodeError:
                return []
        return []

    def set_options_list(self, options: Optional[List[str]]):
        """Convert list to options_json string"""
        if options:
            self.options_json = json.dumps(options)
        else:
            self.options_json = None


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class TaskUpdate(SQLModel):
    type: Optional[TaskType] = None
    question: Optional[str] = None
    options_json: Optional[str] = None
    correct_answer: Optional[str] = None
    course_id: Optional[UUID] = None
