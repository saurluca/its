from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from enum import Enum

if TYPE_CHECKING:
    from documents.models import Chunk


class TaskType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"


class TaskBase(SQLModel):
    type: TaskType
    question: str
    correct_answer: str


class Task(TaskBase, table=True):
    id: UUID | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    chunks: list["Chunk"] = Relationship(
        back_populates="tasks",
        link_model="ChunkTaskLink",
    )
    answer_options: list["AnswerOption"] = Relationship(
        back_populates="task",
    )


class TaskCreate(TaskBase):
    pass


class TaskUpdate(SQLModel):
    question: str | None = None
    # TODO correct_answer: str | None = None
    chunk_id: UUID | None = None


class TaskDelete(SQLModel):
    pass


class AnswerOption(SQLModel, table=True):
    task_id: UUID | None = Field(default=None, foreign_key="task.id", primary_key=True)
    answer: str = Field(primary_key=True)  # Make answer part of composite primary key
    is_correct: bool

    # Relationships
    task: "Task" = Relationship(back_populates="answer_options")
