from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from documents.models import Chunk
from repositories.models import Repository, RepositoryTaskLink
from constants import DEFAULT_NUM_TASKS


if TYPE_CHECKING:
    from skills.models import Skill
    from auth.models import User


class TaskType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"


class AnswerOptionBase(SQLModel):
    answer: str
    is_correct: bool


class AnswerOption(AnswerOptionBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="task.id", nullable=False)

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


# many to many task to user with tracking fields
class TaskUserLink(SQLModel, table=True):
    task_id: UUID = Field(foreign_key="task.id", primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", primary_key=True)
    times_correct: int = Field(
        default=0, description="Number of times user answered correctly"
    )
    times_incorrect: int = Field(
        default=0, description="Number of times user answered incorrectly"
    )
    times_partial: int = Field(
        default=0, description="Number of times user got partial credit"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None


class TaskBase(SQLModel):
    type: TaskType
    question: str
    chunk_id: UUID = Field(foreign_key="chunk.id")


class Task(TaskBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    skill_id: UUID | None = Field(
        foreign_key="skill.id", nullable=True
    )  # Optional skill assignment
    created_at: datetime = Field(default_factory=datetime.now)
    deleted_at: datetime | None = None

    # Relationships
    chunk: "Chunk" = Relationship(back_populates="tasks")
    answer_options: list["AnswerOption"] = Relationship(
        back_populates="task",
        cascade_delete=True,
    )
    repositories: list["Repository"] = Relationship(
        back_populates="tasks",
        link_model=RepositoryTaskLink,
    )
    skill: "Skill" = Relationship(back_populates="tasks")
    # Track user interactions with this task
    users: list["User"] = Relationship(
        back_populates="tasks",
        link_model=TaskUserLink,
    )


class TaskCreate(TaskBase):
    answer_options: list[AnswerOptionCreate] | None = None
    skill_id: UUID | None = None  # Optional skill assignment


class TaskUpdate(SQLModel):
    question: str | None = None
    type: TaskType | None = None
    chunk_id: UUID | None = None
    skill_id: UUID | None = None  # Optional skill assignment
    answer_options: list[AnswerOptionCreate] | None = None


class TaskDelete(SQLModel):
    pass


class TaskRead(TaskBase):
    id: UUID
    skill_id: UUID | None = None
    created_at: datetime
    deleted_at: datetime | None = None
    answer_options: list["AnswerOption"] = []


# Used for the teacher model to provide feedback
class TaskReadTeacher(SQLModel):
    question: str = Field(..., description="The question being asked.")
    answer_options: list["AnswerOption"] = Field(
        default=[],
        description="A list of answer options for the question. Including which answers are correct and which are not.",
    )
    chunk: "Chunk" = Field(
        ...,
        description="The chunk of text related to the question. Source of truth for the question and answer options.",
    )


class TeacherResponseMultipleChoice(SQLModel):
    feedback: str


class TeacherResponseFreeText(SQLModel):
    score: int
    feedback: str


class EvaluateAnswerRequest(SQLModel):
    student_answer: str


class GenerateTasksForDocumentsRequest(SQLModel):
    repository_id: UUID
    document_ids: list[UUID]
    num_tasks: int = DEFAULT_NUM_TASKS
    task_type: str = "multiple_choice"


class TaskUserProgress(SQLModel):
    task_id: UUID
    times_correct: int
    times_incorrect: int
    times_partial: int
    updated_at: datetime


# Rebuild models to resolve forward references
TaskReadTeacher.model_rebuild()
