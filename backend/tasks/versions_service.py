from uuid import UUID, uuid4
from datetime import datetime
from sqlmodel import Session, select, func
from typing import List, Optional

from tasks.versions import TaskVersion, AnswerOptionVersion
from tasks.models import Task, TaskType, AnswerOption
from documents.models import Chunk
from skills.models import Skill

def create_task_snapshot(session: Session, task: Task) -> TaskVersion:
    """
    Create a complete snapshot of a task and all its answer options.
    This is the main function to call before modifying or deleting a task.
    """
    # Get next version number
    next_version = get_next_version_number(session, task.id)
    
    # Create task version
    task_version = TaskVersion(
        id=uuid4(),
        task_id=task.id,
        version=next_version,
        question=task.question,
        type=task.type,
        chunk_id=task.chunk_id,
        skill_id=task.skill_id,
        created_at=datetime.utcnow(),
    )
    session.add(task_version)
    session.flush()  # Get the task_version.id for foreign key
    
    # Snapshot all answer options
    answer_options = session.exec(
        select(AnswerOption).where(AnswerOption.task_id == task.id)
    ).all()
    
    for opt in answer_options:
        opt_version = AnswerOptionVersion(
            id=uuid4(),
            answer_option_id=opt.id,
            task_version_id=task_version.id,
            answer=opt.answer,
            is_correct=opt.is_correct,
            created_at=datetime.utcnow(),
        )
        session.add(opt_version)
    
    return task_version

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
    """Create a new version of a task (legacy function - prefer create_task_snapshot)"""
    task_version = TaskVersion(
        id=uuid4(),
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
        id=uuid4(),
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