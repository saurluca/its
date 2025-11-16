from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from typing import TYPE_CHECKING

from tasks.models import TaskType

if TYPE_CHECKING:
    from tasks.models import Task, AnswerOption
    from documents.models import Chunk
    from skills.models import Skill


class TaskVersion(SQLModel, table=True):
    """
    Immutable snapshot of a task at a moment in time.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    task_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("task.id", ondelete="RESTRICT"),
            index=True
        )
    )
    version: int = Field(index=True)

    question: str  # Matches Task.question
    type: TaskType  # Matches Task.type

    chunk_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("chunk.id", ondelete="RESTRICT"),
            index=True
        )
    )
    skill_id: UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("skill.id", ondelete="SET NULL"),
            nullable=True
        )
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    task: "Task" = Relationship(back_populates="versions")
    chunk: "Chunk" = Relationship(back_populates="task_versions")
    skill: "Skill" = Relationship(back_populates="task_versions")
    answer_option_versions: list["AnswerOptionVersion"] = Relationship(
        back_populates="task_version"
    )

    __table_args__ = (
        UniqueConstraint("task_id", "version"),
    )


class AnswerOptionVersion(SQLModel, table=True):
    """
    Immutable snapshot of an answer option belonging to a TaskVersion.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    answer_option_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("answeroption.id", ondelete="RESTRICT"),
            index=True
        )
    )
    task_version_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("taskversion.id", ondelete="CASCADE"),
            index=True
        )
    )

    answer: str
    is_correct: bool

    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    answer_option: "AnswerOption" = Relationship(back_populates="versions")
    task_version: "TaskVersion" = Relationship(back_populates="answer_option_versions")