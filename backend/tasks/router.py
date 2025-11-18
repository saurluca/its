from fastapi import APIRouter, status, Depends, HTTPException, Query, Body
import asyncio
import json
from datetime import datetime
from dependencies import (
    get_db_session,
    get_large_llm,
    get_large_llm_no_cache,
)
from documents.models import Chunk, Document
from tasks.models import (
    Task,
    TaskCreate,
    TaskUpdate,
    TaskRead,
    TaskReadWithUserProgress,
    TaskType,
    AnswerOption,
    AnswerOptionCreate,
    AnswerOptionUpdate,
    AnswerOptionRead,
    EvaluateAnswerRequest,
    TaskReadTeacher,
    TeacherResponseMultipleChoice,
    TeacherResponseFreeText,
    GenerateTasksForDocumentsRequest,
    TaskUserLink,
    ResultType,
    TaskAnswerEvent
)
from repositories.access_control import (
    create_task_access_dependency,
    create_repository_access_dependency,
    create_document_access_dependency,
    create_chunk_access_dependency,
    create_unit_access_dependency,
)
from analytics.queries import (
    get_task_snapshot, get_task_answer_history, 
    get_latest_task_snapshot, get_task_version_history, 
    compare_task_versions, get_task_completion_stats, 
    get_task_user_attempts, get_task_change_history
    )
from repositories.models import (
    Repository,
    AccessLevel,
    RepositoryAccess,
    RepositoryDocumentLink,
)
from units.models import Unit, UnitTaskLink
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse, User
from uuid import UUID
from typing import Any, cast, Optional
from sqlalchemy import update
from sqlmodel import select, Session
from tasks.service import (
    generate_tasks,
    evaluate_student_answer,
    get_study_tasks_for_unit,
)
import dspy
from repositories.access_control import get_repository_access
from tasks.versions_service import create_task_snapshot
from tasks.models import ChangeType, TaskChangeEvent
from tasks.stats_service import increment_task_deleted, increment_task_modified
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/{task_id}/answer")
def submit_answer(
    task_id: UUID,
    *,
    option_id: Optional[UUID] = Body(None, embed=True),
    text: Optional[str] = Body(None, embed=True),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request),
    lm: dspy.LM = Depends(get_large_llm),
):
    """
    Submit a student answer.
    - MULTIPLE_CHOICE: send `option_id`
    - FREE_TEXT:       send `text`
    """
    # 1. Load task
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    # 2. Prepare teacher model (only for FREE_TEXT)
    task_teacher: Optional[TaskReadTeacher] = None
    if task.type == TaskType.FREE_TEXT:
        correct_opt = session.exec(
            select(AnswerOption)
            .where(AnswerOption.task_id == task_id)
            .where(AnswerOption.is_correct)
        ).first()
        if not correct_opt:
            raise HTTPException(500, "No correct answer defined for free-text task")

        task_teacher = TaskReadTeacher(
            chunk=task.chunk,
            question=task.question,
            answer_options=[correct_opt],
        )

    # 3. Determine result
    result: ResultType
    answer_option_id: Optional[UUID] = None
    user_answer_text: Optional[str] = None
    score: Optional[int] = None
    feedback: Optional[str] = None

    if task.type == TaskType.MULTIPLE_CHOICE:
        # ────── MULTIPLE CHOICE ──────
        if not option_id:
            raise HTTPException(400, "option_id required")
        opt = session.get(AnswerOption, option_id)
        if not opt or opt.task_id != task_id:
            raise HTTPException(400, "Invalid option")
        answer_option_id = option_id
        result = ResultType.CORRECT if opt.is_correct else ResultType.INCORRECT

    else:
        # ────── FREE TEXT ──────
        if text is None:
            raise HTTPException(400, "text required")
        user_answer_text = text

        if not task_teacher:
            raise HTTPException(500, "Teacher model not prepared")
        
        teacher_response = evaluate_student_answer(
            task_teacher=task_teacher,
            student_answer=text,
            task_type=task.type,
            lm=lm,
        )

        if isinstance(teacher_response, TeacherResponseFreeText):
            score = teacher_response.score
            feedback = teacher_response.feedback
            if score >= 90:
                result = ResultType.CORRECT
            elif score >= 50:
                result = ResultType.PARTIAL
            else:
                result = ResultType.INCORRECT
        else:
            result = ResultType.PARTIAL  # fallback

    answer_event = TaskAnswerEvent(
        task_id=task_id,
        user_id=current_user.id,
        answer_option_id=answer_option_id,
        user_answer_text=user_answer_text,
        result=result,
    )
    session.add(answer_event)

    link = session.exec(
        select(TaskUserLink)
        .where(TaskUserLink.task_id == task_id)
        .where(TaskUserLink.user_id == current_user.id)
    ).first()

    if not link:
        link = TaskUserLink(task_id=task_id, user_id=current_user.id)
        session.add(link)

    if result == ResultType.CORRECT:
        link.times_correct += 1
    elif result == ResultType.INCORRECT:
        link.times_incorrect += 1
    else:
        link.times_partial += 1

    link.updated_at = datetime.utcnow()
    session.commit()

    return {
        "task_id": str(task_id),
        "result": result.value,
        "answer_option_id": str(answer_option_id) if answer_option_id else None,
        "user_answer_text": user_answer_text,
        "score": score,
        "feedback": feedback,
    }

@router.get("/{task_id}/snapshot/{version}")
def task_snapshot(
    task_id: UUID, 
    version: int, 
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get a specific version snapshot of a task"""
    snapshot = get_task_snapshot(session, task_id, version)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Version not found")
    return snapshot


@router.get("/{task_id}/snapshot/latest")
def latest_task_snapshot(
    task_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get the latest version snapshot of a task"""
    snapshot = get_latest_task_snapshot(session, task_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Task not found")
    return snapshot


@router.get("/{task_id}/versions")
def get_versions(
    task_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get all version numbers and timestamps for a task"""
    versions = get_task_version_history(session, task_id)
    
    return {
        "task_id": task_id,
        "total_versions": len(versions),
        "versions": versions
    }


@router.get("/{task_id}/compare")
def compare_versions(
    task_id: UUID,
    version1: int = Query(..., description="First version to compare"),
    version2: int = Query(..., description="Second version to compare"),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Compare two versions of a task"""
    comparison = compare_task_versions(session, task_id, version1, version2)
    
    if not comparison:
        raise HTTPException(status_code=404, detail="One or both versions not found")
    
    return comparison

# =========================TASK STATISTICS ENDPOINTS======================

@router.get("/{task_id}/stats")
def task_stats(
    task_id: UUID, 
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get completion statistics for a task"""
    return get_task_completion_stats(session, task_id)


@router.get("/{task_id}/user-attempts")
def task_user_attempts(
    task_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get individual user attempts for a task (paginated)"""
    attempts = get_task_user_attempts(session, task_id, limit, offset)
    
    return {
        "task_id": task_id,
        "attempts": [{
            "user_id": a.user_id,
            "times_correct": a.times_correct,
            "times_incorrect": a.times_incorrect,
            "times_partial": a.times_partial,
            "last_answered_at": a.updated_at
        } for a in attempts],
        "limit": limit,
        "offset": offset
    }

# ===========================TASK HISTORY ENDPOINTS===========================

@router.get("/{task_id}/answer-history")
def task_answer_history(
    task_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get answer history for a task"""
    return get_task_answer_history(session, task_id, limit, offset)


@router.get("/{task_id}/change-history")
def task_change_history(
    task_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get change history for a task"""
    return get_task_change_history(session, task_id, limit, offset)

# ----

# Updated to Filter out soft-deleted tasks
@router.get("", response_model=list[TaskRead])
async def get_tasks(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all tasks the current user has access to via repository-unit links."""
    # Get tasks accessible through repositories -> units the user has access to
    accessible_tasks = session.exec(
        select(Task)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .join(Unit, UnitTaskLink.unit_id == Unit.id)
        .join(Repository, Unit.repository_id == Repository.id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (Repository.owner_id == current_user.id)
            | (RepositoryAccess.user_id == current_user.id)
        )
        .where(Task.deleted_at.is_(None))
        .distinct()
    ).all()

    return accessible_tasks


@router.get("/chunk/{chunk_id}", response_model=list[TaskRead])
async def get_tasks_by_chunk(
    chunk_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_chunk_access_dependency(AccessLevel.READ)
    ),
):
    """
    Get all tasks for a specific chunk if user has read access.
    """
    # Verify chunk exists
    db_chunk = session.get(Chunk, chunk_id)
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
        )

    db_tasks = session.exec(select(Task).where(Task.chunk_id == chunk_id)).all()
    return db_tasks


@router.get("/document/{document_id}", response_model=list[TaskRead])
async def get_tasks_by_document(
    document_id: str,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.READ, "document_id")
    ),
):
    """
    Get all tasks for a specific document by fetching tasks from all chunks of that document.
    Requires read access to the document via repository links.
    """
    # Get all chunks for the document
    chunks = session.exec(select(Chunk).where(Chunk.document_id == document_id)).all()
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No chunks found for document"
        )

    # Get chunk IDs
    chunk_ids = [chunk.id for chunk in chunks]

    # Get all tasks for these chunks
    db_tasks = session.exec(
        select(Task).where(cast(Any, Task.chunk_id).in_(chunk_ids))
    ).all()
    return db_tasks


@router.get("/unit/{unit_id}", response_model=list[TaskRead])
async def get_tasks_by_unit(
    unit_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_unit_access_dependency(AccessLevel.READ)
    ),
):
    """
    Get all tasks for a specific unit.
    Requires read access to the unit via repository links.
    """
    # Get the unit to verify it exists
    unit = session.get(Unit, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found",
        )

    # Get all tasks directly linked to this unit
    db_tasks = session.exec(
        select(Task)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .where(UnitTaskLink.unit_id == unit_id)
        .where(Task.deleted_at.is_(None))
    ).all()

    return db_tasks


@router.get("/repository/{repository_id}", response_model=list[TaskRead])
async def get_tasks_by_repository(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.READ)
    ),
):
    """
    Get all tasks for a specific repository through the repository-unit-task relationship.
    Requires read access to the repository.
    """
    # Get the repository to verify it exists
    repository = session.get(Repository, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Get all tasks linked to this repository through units, Filter out soft-deleted tasks
    db_tasks = session.exec(
        select(Task)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .join(Unit, UnitTaskLink.unit_id == Unit.id)
        .where(Unit.repository_id == repository_id)
        .where(Task.deleted_at.is_(None))
    ).all()

    return db_tasks


@router.get("/{task_id}", response_model=TaskReadWithUserProgress)
async def get_task(
    task_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.READ)
    ),
):
    """Get a specific task if user has read access via repository links.
    Includes per-user progress counters for the current user.
    """
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    # Fetch per-user link if any
    link = session.exec(
        select(TaskUserLink).where(
            TaskUserLink.task_id == task_id, TaskUserLink.user_id == current_user.id
        )
    ).one_or_none()

    user_progress = None
    if link is not None:
        user_progress = {
            "times_correct": link.times_correct,
            "times_incorrect": link.times_incorrect,
            "times_partial": link.times_partial,
            "updated_at": link.updated_at,
        }

    # Compose response model with embedded user progress
    # Pydantic/SQLModel will coerce dict to TaskUserProgress
    return TaskReadWithUserProgress(
        id=db_task.id,
        type=db_task.type,
        question=db_task.question,
        chunk_id=db_task.chunk_id,
        skill_id=db_task.skill_id,
        created_at=db_task.created_at,
        deleted_at=db_task.deleted_at,
        answer_options=db_task.answer_options,
        user_progress=user_progress,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TaskRead)
async def create_task(
    task: TaskCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a task if user has write access to repositories containing the chunk's document."""

    # TODO rewrite function to fit current use case in frontend, espacially access control

    # Verify chunk exists
    db_chunk = session.get(Chunk, task.chunk_id)
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
        )

    repository_links = session.exec(
        select(RepositoryDocumentLink).where(
            RepositoryDocumentLink.document_id == db_chunk.document_id
        )
    ).all()

    if not repository_links:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create task: Document not linked to any repository",
        )

    # Check write access to at least one repository
    access_granted = False
    for link in repository_links:
        try:
            await get_repository_access(
                link.repository_id, AccessLevel.WRITE, session, current_user
            )
            access_granted = True
            break
        except HTTPException:
            continue

    if not access_granted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Write access required to repositories containing this document",
        )

    # Extract answer options from the request
    answer_options_data = task.answer_options or []
    task_data = task.model_dump(exclude={"answer_options"})

    # Create the task
    db_task = Task(**task_data)
    session.add(db_task)
    session.flush()  # Flush to get the task ID

    # Create answer options
    for answer_option_data in answer_options_data:
        db_answer_option = AnswerOption(
            task_id=db_task.id, **answer_option_data.model_dump()
        )
        session.add(db_answer_option)

    session.commit()
    session.refresh(db_task)
    return db_task


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: UUID,
    task: TaskUpdate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.WRITE)
    ),
):
    """Update a task and create a version snapshot"""
    
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    if task.chunk_id is not None:
        db_chunk = session.get(Chunk, task.chunk_id)
        if not db_chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
            )

    # Track changes
    changes = {}
    if task.question and task.question != db_task.question:
        changes["question"] = {"old": db_task.question, "new": task.question}
    if task.type and task.type != db_task.type:
        changes["type"] = {"old": db_task.type.value, "new": task.type.value}
    if task.chunk_id and task.chunk_id != db_task.chunk_id:
        changes["chunk_id"] = {"old": str(db_task.chunk_id), "new": str(task.chunk_id)}

    # Create snapshot if anything changed
    if changes or task.answer_options is not None:
        new_version = create_task_snapshot(session, db_task)

    # Update task
    task_data = task.model_dump(exclude_unset=True, exclude={"answer_options"})
    db_task.sqlmodel_update(task_data)

    # Handle answer options
    if task.answer_options is not None:
        changes["answer_options"] = "modified"
        
        existing_options = session.exec(
            select(AnswerOption).where(AnswerOption.task_id == task_id)
        ).all()
        
        # Create a mapping of existing option IDs for later reference
        existing_option_ids = {option.id for option in existing_options}
        
        # Find answer events that reference these options
        answer_events = session.exec(
            select(TaskAnswerEvent).where(
                TaskAnswerEvent.answer_option_id.in_(list(existing_option_ids))
            )
        ).all()
        
        # Create a mapping of answer option data to identify matches
        new_options_data = {
            (opt.answer, opt.is_correct): opt for opt in task.answer_options
        }
        
        # Track which options are kept, updated, or deleted
        options_to_keep = []
        options_to_delete = []
        
        for existing_option in existing_options:
            # Check if this option matches any new option
            if (existing_option.answer, existing_option.is_correct) in new_options_data:
                # This option is kept
                options_to_keep.append(existing_option)
                # Remove from new options to avoid duplicates
                del new_options_data[(existing_option.answer, existing_option.is_correct)]
            else:
                # This option will be deleted
                options_to_delete.append(existing_option)
        
        # For options that will be deleted, nullify references in answer events
        for option in options_to_delete:
            session.exec(
                update(TaskAnswerEvent)
                .where(TaskAnswerEvent.answer_option_id == option.id)
                .values(answer_option_id=None)
            )
            session.delete(option)
        
        # Add the new options
        for answer_option_data in new_options_data.values():
            db_answer_option = AnswerOption(
                task_id=task_id, **answer_option_data.model_dump()
            )
            session.add(db_answer_option)

    # Log changes
    if changes:
        change_event = TaskChangeEvent(
            task_id=task_id,
            change_type=ChangeType.MODIFIED,
            user_id=current_user.id,
            old_value=str(changes),
            new_value=task.question if task.question else None,
            change_metadata=json.dumps({
                "version": new_version.version,
                "changes": changes
            })
        )
        session.add(change_event)
        
        unit_link = session.exec(
            select(UnitTaskLink).where(UnitTaskLink.task_id == task_id)
        ).first()
        
        if unit_link:
            unit = session.get(Unit, unit_link.unit_id)
            if unit:
                increment_task_modified(session, unit.repository_id)

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.WRITE)
    ),
):
    """Soft delete a task (marks as deleted but preserves all data)."""    
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    
    # If the task is already deleted, just return success without doing anything else.
    if db_task.deleted_at is not None:
        return {"ok": True, "message": "Task was already deleted", "deleted_at": db_task.deleted_at}
    
    # Create snapshot before soft-deleting
    create_task_snapshot(session, db_task)
    
    # Soft delete
    db_task.deleted_at = datetime.utcnow()
    session.add(db_task)
    
    # Log deletion
    change_event = TaskChangeEvent(
        task_id=task_id,
        change_type=ChangeType.DELETED,
        user_id=current_user.id,
        change_metadata={"deleted_at": db_task.deleted_at.isoformat()}
    )
    session.add(change_event)
    
    # Update stats
    unit_link = session.exec(
        select(UnitTaskLink).where(UnitTaskLink.task_id == task_id)
    ).first()
    
    if unit_link:
        unit = session.get(Unit, unit_link.unit_id)
        if unit:
            increment_task_deleted(session, unit.repository_id)
    
    session.commit()
    return {"ok": True, "message": "Task soft-deleted", "deleted_at": db_task.deleted_at}

# Answer Option specific endpoints
@router.post("/{task_id}/answer-options", response_model=AnswerOptionRead)
async def create_answer_option(
    task_id: UUID,
    answer_option: AnswerOptionCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.WRITE)
    ),
):
    # Verify task exists
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    db_answer_option = AnswerOption(task_id=task_id, **answer_option.model_dump())
    session.add(db_answer_option)
    session.commit()
    session.refresh(db_answer_option)
    return db_answer_option


@router.get("/{task_id}/answer-options", response_model=list[AnswerOptionRead])
async def get_answer_options(
    task_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.READ)
    ),
):
    # Verify task exists
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    answer_options = session.exec(
        select(AnswerOption).where(AnswerOption.task_id == task_id)
    ).all()
    return answer_options


@router.put("/{task_id}/answer-options/{option_id}", response_model=AnswerOptionRead)
async def update_answer_option(
    task_id: UUID,
    option_id: UUID,
    answer_option_update: AnswerOptionUpdate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.WRITE)
    ),
):
    """Update an answer option and log changes"""
    
    
    db_answer_option = session.get(AnswerOption, option_id)
    if not db_answer_option or db_answer_option.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer option not found"
        )
    
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    
    # Track changes
    changes = {}
    if answer_option_update.answer and answer_option_update.answer != db_answer_option.answer:
        changes["answer"] = {"old": db_answer_option.answer, "new": answer_option_update.answer}
    if answer_option_update.is_correct is not None and answer_option_update.is_correct != db_answer_option.is_correct:
        changes["is_correct"] = {"old": db_answer_option.is_correct, "new": answer_option_update.is_correct}
    
    if changes:
        create_task_snapshot(session, task)
        
        change_event = TaskChangeEvent(
            task_id=task.id,
            change_type=ChangeType.MODIFIED,
            user_id=current_user.id,
            answer_option_id=option_id,
            old_value=str(changes),
            metadata={"field": "answer_option", "option_id": str(option_id), "changes": changes}
        )
        session.add(change_event)
    
    update_data = answer_option_update.model_dump(exclude_unset=True)
    db_answer_option.sqlmodel_update(update_data)
    session.add(db_answer_option)
    session.commit()
    session.refresh(db_answer_option)
    return db_answer_option


@router.delete("/{task_id}/answer-options/{option_id}")
async def delete_answer_option(
    task_id: UUID,
    option_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.WRITE)
    ),
):
    db_answer_option = session.get(AnswerOption, option_id)
    if not db_answer_option or db_answer_option.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer option not found"
        )

    session.delete(db_answer_option)
    session.commit()
    return {"ok": True}


@router.post("/generate_for_documents", response_model=list[TaskRead])
async def generate_tasks_for_documents(
    request: GenerateTasksForDocumentsRequest,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """
    Generate tasks for the provided documents and link them to the given unit.
    Runs inline (awaited) and returns the created tasks. No polling or background jobs.
    Requires WRITE access to the repository that contains the unit.
    """
    # Validate max tasks limit
    if request.num_tasks > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum 50 tasks per request allowed",
        )

    # Check unit access (which checks repository access under the hood)
    unit = session.get(Unit, request.unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )

    # Check write access to the repository containing this unit
    try:
        await get_repository_access(
            unit.repository_id, AccessLevel.WRITE, session, current_user
        )
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Write access required to repository containing this unit",
        )

    # Collect forbidden questions already linked to the unit to avoid duplicates
    existing_question_rows = session.exec(
        select(Task.question)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .where(UnitTaskLink.unit_id == request.unit_id)
    ).all()
    forbidden_questions: set[str] = (
        set(existing_question_rows) if existing_question_rows else set()
    )

    created_tasks: list[Task] = []

    # Normalize task type to string for generator
    task_type_value = (
        request.task_type
        if isinstance(request.task_type, str)
        else request.task_type.value  # type: ignore[attr-defined]
    )

    # For each document, generate tasks and persist
    for document_id in request.document_ids:
        chunks_for_doc: list[Chunk] = session.exec(
            select(Chunk).where(Chunk.document_id == document_id, Chunk.important)
        ).all()

        if not chunks_for_doc:
            continue

        lm = get_large_llm_no_cache()
        generated: list[Task] = await asyncio.to_thread(
            generate_tasks,
            document_id,
            chunks_for_doc,
            lm,
            request.num_tasks,
            task_type_value,
            forbidden_questions,
        )

        for task in generated:
            session.add(task)
            session.flush()
            session.add(UnitTaskLink(unit_id=request.unit_id, task_id=task.id))
            if task.question:
                forbidden_questions.add(task.question)
            created_tasks.append(task)

    if created_tasks:
        session.commit()

    return created_tasks


@router.get("/unit/{unit_id}/study", response_model=list[TaskRead])
async def get_study_tasks(
    unit_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_unit_access_dependency(AccessLevel.READ)
    ),
):
    """
    Return an ordered list of tasks for a study session for the given unit,
    tailored to the current user using an SM-2-inspired priority.
    """
    tasks = get_study_tasks_for_unit(unit_id, current_user.id, session)
    return tasks
