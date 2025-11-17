#analytics/queries.py

from uuid import UUID
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload
from tasks.models import TaskAnswerEvent, TaskChangeEvent
from tasks.models import (
    Task,
    TaskUserLink,
    AnswerOption,
    ResultType,
    TaskType
)
from tasks.versions import TaskVersion, AnswerOptionVersion
from tasks.models import ChangeType
from tasks.stats import TaskStatistics
from units.models import UnitTaskEvent
from analytics.models import UserPageSession, PageType

def get_task_completion_stats(session: Session, task_id: UUID) -> Dict[str, Any]:
    """Get aggregated completion statistics for a task"""
    # Get counts
    stmt = select(
        func.count(TaskUserLink.user_id).label('total_users'),
        func.sum(TaskUserLink.times_correct).label('total_correct'),
        func.sum(TaskUserLink.times_incorrect).label('total_incorrect'),
        func.sum(TaskUserLink.times_partial).label('total_partial'),
    ).where(TaskUserLink.task_id == task_id)
    
    result = session.exec(stmt).first()
    
    # Calculate metrics
    total_attempts = (result.total_correct or 0) + (result.total_incorrect or 0) + (result.total_partial or 0)
    success_rate = (result.total_correct / total_attempts * 100) if total_attempts > 0 else 0
    
    return {
        "task_id": task_id,
        "total_users": result.total_users or 0,
        "total_attempts": total_attempts,
        "total_correct": result.total_correct or 0,
        "total_incorrect": result.total_incorrect or 0,
        "total_partial": result.total_partial or 0,
        "success_rate": round(success_rate, 2)
    }


def get_task_user_attempts(
    session: Session, 
    task_id: UUID,
    limit: int = 50,
    offset: int = 0
) -> List[TaskUserLink]:
    """Get individual user attempts for a task (paginated)"""
    stmt = (
        select(TaskUserLink)
        .where(TaskUserLink.task_id == task_id)
        .order_by(TaskUserLink.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    return session.exec(stmt).all()

def get_task_modification_count(session: Session, task_id: UUID) -> int:
    """Get the number of times a task has been modified"""
    stmt = select(func.count(TaskVersion.id)).where(TaskVersion.task_id == task_id)
    count = session.exec(stmt).first()
    return max((count or 1) - 1, 0)


def get_task_version_history(
    session: Session,
    task_id: UUID
) -> List[Dict[str, Any]]:
    """Get all versions of a task with timestamps"""
    stmt = (
        select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version.desc())
    )
    
    versions = session.exec(stmt).all()
    
    return [{
        "version": v.version,
        "question": v.question,
        "type": v.type,
        "created_at": v.created_at
    } for v in versions]


def get_repository_task_statistics(session: Session, repository_id: UUID) -> Dict[str, Any]:
    """Get task statistics for a repository"""
    from tasks.stats_service import get_or_create_task_statistics
    stats = get_or_create_task_statistics(session, repository_id)
    
    return {
        "repository_id": repository_id,
        "total_created": stats.total_created,
        "total_deleted": stats.total_deleted,
        "total_modified": stats.total_modified,
        "last_updated": stats.updated_at
    }


def get_task_answer_history(
    session: Session,
    task_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get recent answer attempts for a task"""
    stmt = (
        select(TaskAnswerEvent)
        .where(TaskAnswerEvent.task_id == task_id)
        .order_by(TaskAnswerEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    events = session.exec(stmt).all()
    
    return {
        "task_id": task_id,
        "events": [{
            "id": e.id,
            "user_id": e.user_id,
            "result": e.result,
            "answer_option_id": e.answer_option_id,
            "user_answer_text": e.user_answer_text,
            "created_at": e.created_at
        } for e in events],
        "limit": limit,
        "offset": offset
    }


def get_user_answer_history(
    session: Session,
    user_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get recent answer attempts by a user"""
    stmt = (
        select(TaskAnswerEvent)
        .where(TaskAnswerEvent.user_id == user_id)
        .order_by(TaskAnswerEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    events = session.exec(stmt).all()
    
    return {
        "user_id": user_id,
        "events": [{
            "id": e.id,
            "task_id": e.task_id,
            "result": e.result,
            "answer_option_id": e.answer_option_id,
            "user_answer_text": e.user_answer_text,
            "created_at": e.created_at
        } for e in events],
        "limit": limit,
        "offset": offset
    }


def get_task_change_history(
    session: Session,
    task_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get change history for a task"""
    stmt = (
        select(TaskChangeEvent)
        .where(TaskChangeEvent.task_id == task_id)
        .order_by(TaskChangeEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    events = session.exec(stmt).all()
    
    return {
        "task_id": task_id,
        "changes": [{
            "id": e.id,
            "change_type": e.change_type,
            "user_id": e.user_id,
            "answer_option_id": e.answer_option_id,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "metadata": e.metadata,
            "created_at": e.created_at
        } for e in events],
        "limit": limit,
        "offset": offset
    }

def get_unit_task_audit(
    session: Session, 
    unit_id: UUID,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Get audit trail for unit-task assignments"""
    stmt = (
        select(UnitTaskEvent)
        .where(UnitTaskEvent.unit_id == unit_id)
        .order_by(UnitTaskEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    events = session.exec(stmt).all()
    
    return {
        "unit_id": unit_id,
        "events": [{
            "id": e.id,
            "task_id": e.task_id,
            "action": e.action,
            "user_id": e.user_id,
            "timestamp": e.created_at
        } for e in events],
        "limit": limit,
        "offset": offset
    }


def get_user_page_time(
    session: Session, 
    user_id: UUID,
    page: Optional[PageType] = None
) -> Dict[str, Any]:
    """Calculate total time spent by user on pages"""
    stmt = select(UserPageSession).where(UserPageSession.user_id == user_id)
    
    if page:
        stmt = stmt.where(UserPageSession.page == page)
    
    sessions = session.exec(stmt).all()
    
    total_seconds = sum([s.duration_seconds or 0 for s in sessions])
    total_sessions = len(sessions)
    avg_session = total_seconds / total_sessions if total_sessions > 0 else 0
    
    return {
        "user_id": user_id,
        "page": page.value if page else "all",
        "total_seconds": total_seconds,
        "total_sessions": total_sessions,
        "average_session_seconds": round(avg_session, 2)
    }


def get_page_usage_stats(
    session: Session,
    page: PageType,
    limit_users: int = 10
) -> Dict[str, Any]:
    """Get usage statistics for a specific page"""
    # Get total sessions and time
    stmt = select(
        func.count(UserPageSession.id).label('total_sessions'),
        func.sum(UserPageSession.duration_seconds).label('total_seconds'),
        func.avg(UserPageSession.duration_seconds).label('avg_seconds')
    ).where(UserPageSession.page == page)
    
    result = session.exec(stmt).first()
    
    # Get top users
    top_users_stmt = (
        select(
            UserPageSession.user_id,
            func.sum(UserPageSession.duration_seconds).label('total_time')
        )
        .where(UserPageSession.page == page)
        .group_by(UserPageSession.user_id)
        .order_by(func.sum(UserPageSession.duration_seconds).desc())
        .limit(limit_users)
    )
    
    top_users = session.exec(top_users_stmt).all()
    
    return {
        "page": page.value,
        "total_sessions": result.total_sessions or 0,
        "total_seconds": result.total_seconds or 0,
        "average_seconds": round(result.avg_seconds or 0, 2),
        "top_users": [{
            "user_id": u.user_id,
            "total_seconds": u.total_time
        } for u in top_users]
    }

def get_task_snapshot(
    session: Session, 
    task_id: UUID, 
    version: int
) -> Optional[Dict[str, Any]]:
    """Get a complete snapshot of a task at a specific version"""
    # Get the task version
    task_version = session.exec(
        select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .where(TaskVersion.version == version)
    ).first()
    
    if not task_version:
        return None
    
    # Get answer option versions
    answer_options = session.exec(
        select(AnswerOptionVersion)
        .where(AnswerOptionVersion.task_version_id == task_version.id)
    ).all()
    
    snapshot = {
        "task_id": task_version.task_id,
        "version": task_version.version,
        "question": task_version.question,
        "type": task_version.type,
        "chunk_id": task_version.chunk_id,
        "skill_id": task_version.skill_id,
        "created_at": task_version.created_at,
        "answer_options": [
            {
                "id": ao.answer_option_id, 
                "answer": ao.answer,
                "is_correct": ao.is_correct
            }
            for ao in answer_options
        ]
    }
    return snapshot


def get_latest_task_snapshot(session: Session, task_id: UUID) -> Optional[Dict[str, Any]]:
    """Get the latest version snapshot of a task"""
    latest_version = session.exec(
        select(func.max(TaskVersion.version))
        .where(TaskVersion.task_id == task_id)
    ).first()
    
    if not latest_version:
        return None
    
    return get_task_snapshot(session, task_id, latest_version)


def compare_task_versions(
    session: Session,
    task_id: UUID,
    version1: int,
    version2: int
) -> Optional[Dict[str, Any]]:
    """Compare two versions of a task"""
    snap1 = get_task_snapshot(session, task_id, version1)
    snap2 = get_task_snapshot(session, task_id, version2)
    
    if not snap1 or not snap2:
        return None
    
    # Determine what changed
    changes = {
        "question_changed": snap1["question"] != snap2["question"],
        "type_changed": snap1["type"] != snap2["type"],
        "chunk_changed": snap1["chunk_id"] != snap2["chunk_id"],
        "skill_changed": snap1["skill_id"] != snap2["skill_id"],
        "answer_options_changed": snap1["answer_options"] != snap2["answer_options"]
    }
    
    return {
        "task_id": task_id,
        "version1": snap1,
        "version2": snap2,
        "changes": changes,
        "has_changes": any(changes.values())
    }


def get_repository_answer_stats(
    session: Session,
    repository_id: UUID
) -> Dict[str, Any]:
    """Get answer statistics for all tasks in a repository"""
    from units.models import Unit, UnitTaskLink
    
    # Get all task IDs in this repository
    task_ids_stmt = (
        select(UnitTaskLink.task_id)
        .join(Unit)
        .where(Unit.repository_id == repository_id)
        .distinct()
    )
    task_ids = [tid for tid in session.exec(task_ids_stmt).all()]
    
    if not task_ids:
        return {
            "repository_id": repository_id,
            "total_answers": 0,
            "total_correct": 0,
            "total_incorrect": 0,
            "total_partial": 0,
            "unique_users": 0,
            "success_rate": 0
        }
    
    # Get answer statistics
    answer_stats = session.exec(
        select(
            func.count(TaskAnswerEvent.id).label('total_answers'),
            func.count(func.distinct(TaskAnswerEvent.user_id)).label('unique_users'),
            func.sum(func.case((TaskAnswerEvent.result == ResultType.CORRECT, 1), else_=0)).label('total_correct'),
            func.sum(func.case((TaskAnswerEvent.result == ResultType.INCORRECT, 1), else_=0)).label('total_incorrect'),
            func.sum(func.case((TaskAnswerEvent.result == ResultType.PARTIAL, 1), else_=0)).label('total_partial')
        )
        .where(TaskAnswerEvent.task_id.in_(task_ids))
    ).first()
    
    total_answers = answer_stats.total_answers or 0
    total_correct = answer_stats.total_correct or 0
    success_rate = (total_correct / total_answers * 100) if total_answers > 0 else 0
    
    return {
        "repository_id": repository_id,
        "total_answers": total_answers,
        "total_correct": total_correct,
        "total_incorrect": answer_stats.total_incorrect or 0,
        "total_partial": answer_stats.total_partial or 0,
        "unique_users": answer_stats.unique_users or 0,
        "success_rate": round(success_rate, 2)
    }


def get_repository_comprehensive_stats(
    session: Session,
    repository_id: UUID
) -> Dict[str, Any]:
    """Get all statistics for a repository"""
    
    # Task lifecycle (created/deleted/modified)
    task_lifecycle = get_repository_task_statistics(session, repository_id)
    
    # Answer analytics
    answer_stats = get_repository_answer_stats(session, repository_id)
    
    return {
        "repository_id": repository_id,
        "task_lifecycle": task_lifecycle,
        "answer_analytics": answer_stats,
        "generated_at": datetime.utcnow()
    }