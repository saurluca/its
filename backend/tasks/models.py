from sqlmodel import SQLModel, Field, Relationship
from typing import TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from enum import Enum
from uuid import uuid4

if TYPE_CHECKING:
    pass


class TaskType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"


class TaskBase(SQLModel):
    type: TaskType
    question: str


class Task(TaskBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    # chunks: list["Chunk"] = Relationship(
    #     back_populates="tasks",
    #     link_model="ChunkTaskLink",
    # )
    answer_options: list["AnswerOption"] = Relationship(
        back_populates="task",
    )


class AnswerOptionBase(SQLModel):
    answer: str
    is_correct: bool


class AnswerOption(AnswerOptionBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="task.id")

    # Relationships
    task: "Task" = Relationship(back_populates="answer_options")


class AnswerOptionCreate(AnswerOptionBase):
    pass


class AnswerOptionUpdate(SQLModel):
    answer: str | None = None
    is_correct: bool | None = None


class AnswerOptionRead(AnswerOptionBase):
    id: UUID
    task_id: UUID


class TaskCreate(TaskBase):
    answer_options: list[AnswerOptionCreate] | None = None


class TaskUpdate(SQLModel):
    question: str | None = None
    type: TaskType | None = None
    chunk_id: UUID | None = None
    answer_options: list[AnswerOptionCreate] | None = None


class TaskDelete(SQLModel):
    pass


class TaskRead(TaskBase):
    id: UUID
    created_at: datetime
    deleted_at: datetime | None = None
    answer_options: list[AnswerOption] = []
