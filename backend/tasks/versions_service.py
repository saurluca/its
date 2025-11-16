from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select, func
from typing import List, Optional

from tasks.versions import TaskVersion, AnswerOptionVersion
from tasks.models import Task, TaskType, AnswerOption
from documents.models import Chunk
from skills.models import Skill


# TaskVersion service functions
def create_task_version(
    session: Session,
    task_id: UUID,
    version: int,
    question: str,
    task_type: TaskType,
    chunk_id: UUID,
    skill_id: Optional[UUID] = None,
    auto_commit: bool = True,
) -> TaskVersion:
    """Create a new version of a task"""
    task_version = TaskVersion(
        task_id=task_id,
        version=version,
        question=question,
        type=task_type,
        chunk_id=chunk_id,
        skill_id=skill_id,
        created_at=datetime.utcnow(),
    )
    
    session.add(task_version)
    
    if auto_commit:
        session.commit()
        session.refresh(task_version)
    
    return task_version


def get_latest_task_version(
    session: Session, task_id: UUID
) -> Optional[TaskVersion]:
    """Get the latest version of a task"""
    return session.exec(
        select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version.desc())
        .limit(1)
    ).first()


def get_all_task_versions(
    session: Session, task_id: UUID
) -> List[TaskVersion]:
    """Get all versions of a task"""
    return session.exec(
        select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version.desc())
    ).all()


def get_next_version_number(session: Session, task_id: UUID) -> int:
    """Get the next version number for a task"""
    max_version = session.exec(
        select(func.max(TaskVersion.version))
        .where(TaskVersion.task_id == task_id)
    ).first()
    
    return (max_version or 0) + 1


# AnswerOptionVersion service functions
def create_answer_option_version(
    session: Session,
    answer_option_id: UUID,
    task_version_id: UUID,
    answer: str,
    is_correct: bool,
    auto_commit: bool = True,
) -> AnswerOptionVersion:
    """Create a new version of an answer option"""
    answer_option_version = AnswerOptionVersion(
        answer_option_id=answer_option_id,
        task_version_id=task_version_id,
        answer=answer,
        is_correct=is_correct,
        created_at=datetime.utcnow(),
    )
    
    session.add(answer_option_version)
    
    if auto_commit:
        session.commit()
        session.refresh(answer_option_version)
    
    return answer_option_version


def get_answer_option_versions_by_task_version(
    session: Session, task_version_id: UUID
) -> List[AnswerOptionVersion]:
    """Get all answer option versions for a specific task version"""
    return session.exec(
        select(AnswerOptionVersion)
        .where(AnswerOptionVersion.task_version_id == task_version_id)
    ).all()