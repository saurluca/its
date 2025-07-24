from typing import List
from uuid import UUID
from sqlmodel import Session, select
from datetime import datetime

from tasks.models import Task, TaskCreate, TaskUpdate
from dependencies import get_database_engine
from exceptions import DocumentNotFoundError


def get_session():
    """Get database session"""
    engine = get_database_engine()
    return Session(engine)


def create_task(task_data: TaskCreate) -> Task:
    """
    Create a new task

    Args:
        task_data: Task creation data

    Returns:
        Created task
    """
    with get_session() as session:
        task = Task.model_validate(task_data.model_dump())
        session.add(task)
        session.commit()
        session.refresh(task)
        return task


def get_task_by_id(task_id: UUID) -> Task:
    """
    Get task by ID

    Args:
        task_id: Task UUID

    Returns:
        Task object

    Raises:
        DocumentNotFoundError: If task not found
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == task_id)
        task = session.exec(statement).first()

        if not task:
            raise DocumentNotFoundError(f"Task not found with id: {task_id}")

        return task


def get_all_tasks(limit: int = 100) -> List[Task]:
    """
    Get all tasks with limit

    Args:
        limit: Maximum number of tasks to return

    Returns:
        List of tasks
    """
    with get_session() as session:
        statement = select(Task).order_by(Task.created_at.desc()).limit(limit)
        tasks = session.exec(statement).all()
        return list(tasks)


def get_tasks_by_course_id(course_id: UUID, limit: int = 100) -> List[Task]:
    """
    Get tasks by course ID

    Args:
        course_id: Course UUID
        limit: Maximum number of tasks to return

    Returns:
        List of tasks for the course
    """
    with get_session() as session:
        statement = (
            select(Task)
            .where(Task.course_id == course_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        tasks = session.exec(statement).all()
        return list(tasks)


def update_task(task_id: UUID, task_update: TaskUpdate) -> Task:
    """
    Update task by ID

    Args:
        task_id: Task UUID
        task_update: Task update data

    Returns:
        Updated task

    Raises:
        DocumentNotFoundError: If task not found
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == task_id)
        task = session.exec(statement).first()

        if not task:
            raise DocumentNotFoundError(f"Task not found with id: {task_id}")

        # Update fields that are not None
        update_data = task_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        task.updated_at = datetime.utcnow()
        session.add(task)
        session.commit()
        session.refresh(task)

        return task


def delete_task(task_id: UUID) -> Task:
    """
    Delete task by ID

    Args:
        task_id: Task UUID

    Returns:
        Deleted task

    Raises:
        DocumentNotFoundError: If task not found
    """
    with get_session() as session:
        statement = select(Task).where(Task.id == task_id)
        task = session.exec(statement).first()

        if not task:
            raise DocumentNotFoundError(f"Task not found with id: {task_id}")

        session.delete(task)
        session.commit()

        return task
