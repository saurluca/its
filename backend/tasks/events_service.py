from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from typing import List, Optional
from sqlalchemy.exc import SQLAlchemyError

from tasks.models import TaskAnswerEvent, TaskChangeEvent
from tasks.models import ChangeType
from tasks.models import Task, ResultType
from auth.models import User


# TaskAnswerEvent service functions
def create_task_answer_event(
    session: Session,
    user_id: UUID,
    task_id: UUID,
    result: ResultType,
    answer_option_id: Optional[UUID] = None,
    user_answer_text: Optional[str] = None,
    auto_commit: bool = True,
) -> TaskAnswerEvent:
    """Create a new task answer event when a user answers a task"""
    try:
        event = TaskAnswerEvent(
            user_id=user_id,
            task_id=task_id,
            answer_option_id=answer_option_id,
            user_answer_text=user_answer_text,
            result=result,
            created_at=datetime.utcnow(),
        )
        
        session.add(event)
        
        if auto_commit:
            session.commit()
            session.refresh(event)
        
        return event
        
    except SQLAlchemyError as e:
        if auto_commit:
            session.rollback()
        raise ValueError(f"Failed to create task answer event: {str(e)}")


def get_task_answer_events_by_task(
    session: Session, task_id: UUID, limit: int = 100
) -> List[TaskAnswerEvent]:
    """Get answer events for a specific task"""
    return session.exec(
        select(TaskAnswerEvent)
        .where(TaskAnswerEvent.task_id == task_id)
        .order_by(TaskAnswerEvent.created_at.desc())
        .limit(limit)
    ).all()


def get_task_answer_events_by_user(
    session: Session, user_id: UUID, limit: int = 100
) -> List[TaskAnswerEvent]:
    """Get answer events for a specific user"""
    return session.exec(
        select(TaskAnswerEvent)
        .where(TaskAnswerEvent.user_id == user_id)
        .order_by(TaskAnswerEvent.created_at.desc())
        .limit(limit)
    ).all()


# TaskChangeEvent service functions
def create_task_change_event(
    session: Session,
    task_id: UUID,
    change_type: ChangeType,
    user_id: Optional[UUID] = None,
    answer_option_id: Optional[UUID] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    metadata: Optional[str] = None,
    auto_commit: bool = True,
) -> TaskChangeEvent:
    """Create a new task change event when a task is modified"""
    try:
        event = TaskChangeEvent(
            task_id=task_id,
            answer_option_id=answer_option_id,
            user_id=user_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )
        
        session.add(event)
        
        if auto_commit:
            session.commit()
            session.refresh(event)
        
        return event
        
    except SQLAlchemyError as e:
        if auto_commit:
            session.rollback()
        raise ValueError(f"Failed to create task change event: {str(e)}")


def get_task_change_events_by_task(
    session: Session, task_id: UUID, limit: int = 100
) -> List[TaskChangeEvent]:
    """Get change events for a specific task"""
    return session.exec(
        select(TaskChangeEvent)
        .where(TaskChangeEvent.task_id == task_id)
        .order_by(TaskChangeEvent.created_at.desc())
        .limit(limit)
    ).all()


def get_task_change_events_by_user(
    session: Session, user_id: UUID, limit: int = 100
) -> List[TaskChangeEvent]:
    """Get change events made by a specific user"""
    return session.exec(
        select(TaskChangeEvent)
        .where(TaskChangeEvent.user_id == user_id)
        .order_by(TaskChangeEvent.created_at.desc())
        .limit(limit)
    ).all()