from typing import TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

from units.models import UnitTaskLink

from constants import DEFAULT_NUM_TASKS


if TYPE_CHECKING:
    from tasks.versions import TaskVersion, AnswerOptionVersion
    from units.models import Unit
    from skills.models import Skill
    from auth.models import User
    from documents.models import Chunk


class TaskType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"


class ResultType(str, Enum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    PARTIAL = "partial"


class AnswerOptionBase(SQLModel):
    answer: str
    is_correct: bool


class ChangeType(str, Enum):
    QUESTION_UPDATE = "question_update"
    OPTION_ADDED = "option_added"
    OPTION_UPDATED = "option_updated"
    OPTION_DELETED = "option_deleted"
    CORRECTNESS_CHANGED = "correctness_changed"
    OTHER = "other"


class TaskChangeEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    task_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("task.id", ondelete="RESTRICT"),
            index=True
        )
    )

    answer_option_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("answeroption.id", ondelete="RESTRICT"),
            nullable=True
        )
    )

    user_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=True
        )
    )

    change_type: ChangeType
    old_value: str | None = None
    new_value: str | None = None
    change_metadata: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    task: "Task" = Relationship(back_populates="change_events")
    user: "User" = Relationship(back_populates="task_change_events")


class TaskAnswerEvent(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("user.id", ondelete="RESTRICT"),
            index=True
        )
    )

    task_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("task.id", ondelete="RESTRICT"),
            index=True
        )
    )

    answer_option_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("answeroption.id", ondelete="RESTRICT"),
            nullable=True
        )
    )

    user_answer_text: str | None = None
    result: ResultType

    created_at: datetime = Field(default_factory=datetime.utcnow)

    task: "Task" = Relationship(back_populates="answer_events")
    user: "User" = Relationship(back_populates="task_answer_events")


class AnswerOption(AnswerOptionBase, table=True):
    id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="task.id", nullable=False)

    # Relationships
    task: "Task" = Relationship(back_populates="answer_options")
    versions: list["AnswerOptionVersion"] = Relationship(back_populates="answer_option")


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
    units: list["Unit"] = Relationship(
        back_populates="tasks",
        link_model=UnitTaskLink,
    )
    skill: "Skill" = Relationship(back_populates="tasks")
    # Track user interactions with this task
    users: list["User"] = Relationship(
        back_populates="tasks",
        link_model=TaskUserLink,
    )
    has_been_modified: bool = Field(default=False)
    versions: list["TaskVersion"] = Relationship(back_populates="task")
    answer_events: list["TaskAnswerEvent"] = Relationship(back_populates="task")
    change_events: list["TaskChangeEvent"] = Relationship(back_populates="task")
    unit_links: list["UnitTaskLink"] = Relationship(back_populates="task")


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


# Per-user progress (read model)
class TaskUserProgress(SQLModel):
    times_correct: int = 0
    times_incorrect: int = 0
    times_partial: int = 0
    updated_at: datetime | None = None


# Task with embedded current-user progress
class TaskReadWithUserProgress(TaskRead):
    user_progress: TaskUserProgress | None = None


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
    unit_id: UUID
    document_ids: list[UUID]
    num_tasks: int = DEFAULT_NUM_TASKS
    task_type: str = "multiple_choice"


# Rebuild models to resolve forward references - all rebuilds are handled (now) at the entry point (main.py)
# TaskReadTeacher.model_rebuild()
