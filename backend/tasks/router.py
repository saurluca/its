from fastapi import APIRouter, status, Depends, HTTPException
import asyncio
from datetime import datetime
from dependencies import (
    get_db_session,
    get_large_llm,
    get_large_llm_no_cache,
)
from documents.models import Chunk
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
)
from repositories.access_control import (
    create_task_access_dependency,
    create_repository_access_dependency,
    create_document_access_dependency,
    create_chunk_access_dependency,
    create_unit_access_dependency,
)
from repositories.models import (
    Repository,
    AccessLevel,
    RepositoryAccess,
    RepositoryDocumentLink,
)
from units.models import Unit, UnitTaskLink
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse
from uuid import UUID
from typing import Any, cast
from sqlmodel import select, Session
from tasks.service import (
    generate_tasks,
    evaluate_student_answer,
    get_study_tasks_for_unit,
)
import dspy
from repositories.access_control import get_repository_access

router = APIRouter(prefix="/tasks", tags=["tasks"])


# TODO is this even needed?
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

    # Get all tasks linked to this repository through units
    db_tasks = session.exec(
        select(Task)
        .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
        .join(Unit, UnitTaskLink.unit_id == Unit.id)
        .where(Unit.repository_id == repository_id)
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
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Verify chunk exists if chunk_id is being updated
    if task.chunk_id is not None:
        db_chunk = session.get(Chunk, task.chunk_id)
        if not db_chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
            )

    # Update task fields
    task_data = task.model_dump(exclude_unset=True, exclude={"answer_options"})
    db_task.sqlmodel_update(task_data)

    # Handle answer options update
    if task.answer_options is not None:
        # Delete existing answer options
        existing_options = session.exec(
            select(AnswerOption).where(AnswerOption.task_id == task_id)
        ).all()
        for option in existing_options:
            session.delete(option)

        # Create new answer options
        for answer_option_data in task.answer_options:
            db_answer_option = AnswerOption(
                task_id=task_id, **answer_option_data.model_dump()
            )
            session.add(db_answer_option)

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
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Explicitly delete answer options first to ensure proper cleanup
    answer_options = session.exec(
        select(AnswerOption).where(AnswerOption.task_id == task_id)
    ).all()
    for answer_option in answer_options:
        session.delete(answer_option)

    # Then delete the task
    session.delete(db_task)
    session.commit()
    return {"ok": True}


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
    db_answer_option = session.get(AnswerOption, option_id)
    if not db_answer_option or db_answer_option.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer option not found"
        )

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


@router.post(
    "/evaluate_answer/{task_id}",
    response_model=TeacherResponseMultipleChoice | TeacherResponseFreeText,
)
async def evaluate_answer(
    task_id: UUID,
    request: EvaluateAnswerRequest,
    session: Session = Depends(get_db_session),
    lm: dspy.LM = Depends(get_large_llm),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.READ)
    ),
):
    """
    Evaluate a student's answer for a specific task.
    Returns feedback on the student's answer.
    """
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Multiple-choice can be short-circuited without LLM if correct
    if db_task.type == TaskType.MULTIPLE_CHOICE:
        correct_options = [
            opt.answer.strip().lower()
            for opt in db_task.answer_options
            if opt.is_correct
        ]
        student = (request.student_answer or "").strip().lower()

        if student in correct_options:
            # Persist as correct and return simple feedback (no LLM call)
            try:
                link = session.exec(
                    select(TaskUserLink).where(
                        TaskUserLink.task_id == task_id,
                        TaskUserLink.user_id == current_user.id,
                    )
                ).one_or_none()
                if link is None:
                    link = TaskUserLink(task_id=task_id, user_id=current_user.id)
                    session.add(link)
                    session.flush()
                link.times_correct += 1
                link.updated_at = datetime.now()
                session.add(link)
                session.commit()
            except Exception:
                session.rollback()
            return TeacherResponseMultipleChoice(feedback="Correct.")

        # Incorrect MC: call LLM for feedback, then persist as incorrect
        task_teacher = TaskReadTeacher(
            question=db_task.question,
            answer_options=db_task.answer_options,
            chunk=db_task.chunk,
        )
        response = await asyncio.to_thread(
            evaluate_student_answer,
            task_teacher,
            request.student_answer,
            db_task.type,
            lm,
        )
        try:
            link = session.exec(
                select(TaskUserLink).where(
                    TaskUserLink.task_id == task_id,
                    TaskUserLink.user_id == current_user.id,
                )
            ).one_or_none()
            if link is None:
                link = TaskUserLink(task_id=task_id, user_id=current_user.id)
                session.add(link)
                session.flush()
            link.times_incorrect += 1
            link.updated_at = datetime.now()
            session.add(link)
            session.commit()
        except Exception:
            session.rollback()
        return response

    # Free text: use LLM scoring
    task_teacher = TaskReadTeacher(
        question=db_task.question,
        answer_options=db_task.answer_options,
        chunk=db_task.chunk,
    )
    response = await asyncio.to_thread(
        evaluate_student_answer,
        task_teacher,
        request.student_answer,
        db_task.type,
        lm,
    )
    # Persist according to score mapping
    try:
        if isinstance(response, TeacherResponseFreeText):
            score_value = response.score
            link = session.exec(
                select(TaskUserLink).where(
                    TaskUserLink.task_id == task_id,
                    TaskUserLink.user_id == current_user.id,
                )
            ).one_or_none()
            if link is None:
                link = TaskUserLink(task_id=task_id, user_id=current_user.id)
                session.add(link)
                session.flush()
            if score_value == 0:
                link.times_correct += 1
            elif score_value == 1:
                link.times_partial += 1
            else:
                link.times_incorrect += 1
            link.updated_at = datetime.now()
            session.add(link)
            session.commit()
    except Exception:
        session.rollback()
    return response


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
