from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select

from tasks.stats import TaskStatistics
from repositories.models import Repository


def get_or_create_task_statistics(
    session: Session, repository_id: UUID
) -> TaskStatistics:
    """Get or create task statistics for a repository"""
    stats = session.exec(
        select(TaskStatistics).where(
            TaskStatistics.repository_id == repository_id
        )
    ).first()
    
    if not stats:
        stats = TaskStatistics(
            repository_id=repository_id,
            total_created=0,
            total_deleted=0,
            total_modified=0,
            updated_at=datetime.utcnow(),
        )
        session.add(stats)
        session.commit()
        session.refresh(stats)
    
    return stats


def increment_task_created(
    session: Session, repository_id: UUID
) -> TaskStatistics:
    """Increment the total_created count for a repository"""
    stats = get_or_create_task_statistics(session, repository_id)
    stats.total_created += 1
    stats.updated_at = datetime.utcnow()
    
    session.add(stats)
    session.commit()
    session.refresh(stats)
    
    return stats


def increment_task_deleted(
    session: Session, repository_id: UUID
) -> TaskStatistics:
    """Increment the total_deleted count for a repository"""
    stats = get_or_create_task_statistics(session, repository_id)
    stats.total_deleted += 1
    stats.updated_at = datetime.utcnow()
    
    session.add(stats)
    session.commit()
    session.refresh(stats)
    
    return stats


# 1. Counts EVERY edit → used by PUT /tasks/{id}, delete endpoint, etc.
def increment_task_modified(session: Session, repository_id: UUID) -> TaskStatistics:
    stats = get_or_create_task_statistics(session, repository_id)
    stats.total_modified += 1
    stats.updated_at = datetime.utcnow()
    session.add(stats)
    session.commit()
    session.refresh(stats)
    return stats


# 2. Counts only the FIRST edit of a task → used only by the advanced versioning helper
def increment_task_modified_once(session: Session, repository_id: UUID, task_id: UUID) -> TaskStatistics:
    from tasks.models import Task
    task = session.get(Task, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    if task.has_been_modified:
        return get_or_create_task_statistics(session, repository_id)

    task.has_been_modified = True
    stats = get_or_create_task_statistics(session, repository_id)
    stats.total_modified += 1
    stats.updated_at = datetime.utcnow()

    session.add(task)
    session.add(stats)
    session.commit()
    session.refresh(stats)
    return stats


def get_task_statistics(
    session: Session, repository_id: UUID
) -> TaskStatistics:
    """Get task statistics for a repository"""
    return get_or_create_task_statistics(session, repository_id)