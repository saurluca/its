from fastapi import APIRouter, status, Depends, HTTPException
from dependencies import get_db_session, get_large_llm, get_large_llm_no_cache
from documents.models import Chunk
from tasks.models import (
    Task,
    TaskCreate,
    TaskUpdate,
    TaskRead,
    AnswerOption,
    AnswerOptionCreate,
    AnswerOptionUpdate,
    AnswerOptionRead,
    EvaluateAnswerRequest,
    TaskReadTeacher,
    TeacherResponseMultipleChoice,
    TeacherResponseFreeText,
    GenerateTasksForMultipleDocumentsRequest,
)
from repositories.access_control import (
    create_task_access_dependency,
    create_repository_access_dependency,
    create_document_access_dependency,
    create_chunk_access_dependency,
)
from repositories.models import (
    Repository,
    RepositoryTaskLink,
    AccessLevel,
    RepositoryAccess,
    RepositoryDocumentLink,
)
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse
from uuid import UUID
from typing import Any, cast
from sqlmodel import select, Session
from tasks.service import generate_tasks, evaluate_student_answer
from constants import DEFAULT_NUM_TASKS
import dspy

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskRead])
async def get_tasks(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all tasks the current user has access to via repository links."""
    # Get tasks accessible through repositories the user has access to
    accessible_tasks = session.exec(
        select(Task)
        .join(RepositoryTaskLink, Task.id == RepositoryTaskLink.task_id)
        .join(Repository, RepositoryTaskLink.repository_id == Repository.id)
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


@router.get("/repository/{repository_id}", response_model=list[TaskRead])
async def get_tasks_by_repository(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.READ)
    ),
):
    """
    Get all tasks for a specific repository using the direct task-repository relationship.
    Requires read access to the repository.
    """
    # Get the repository to verify it exists
    repository = session.get(Repository, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Get all tasks directly linked to this repository
    db_tasks = session.exec(
        select(Task)
        .join(RepositoryTaskLink, Task.id == RepositoryTaskLink.task_id)
        .where(RepositoryTaskLink.repository_id == repository_id)
    ).all()

    return db_tasks


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_task_access_dependency(AccessLevel.READ)
    ),
):
    """Get a specific task if user has read access via repository links."""
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return db_task


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TaskRead)
async def create_task(
    task: TaskCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a task if user has write access to repositories containing the chunk's document."""
    # Verify chunk exists
    db_chunk = session.get(Chunk, task.chunk_id)
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
        )

    # Check if user has write access to any repository containing this chunk's document
    from repositories.access_control import get_repository_access

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


@router.post("/generate/{doc_id}", response_model=list[TaskRead])
async def generate_tasks_from_document(
    doc_id: UUID,
    repository_id: UUID | None = None,
    num_tasks: int = DEFAULT_NUM_TASKS,
    task_type: str = "multiple_choice",
    session: Session = Depends(get_db_session),
    lm: dspy.LM = Depends(get_large_llm_no_cache),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.WRITE, "doc_id")
    ),
):
    """
    Generates a specified number of questions for a given document ID.
    Uses the document's chunks to create questions and answer options.
    Optionally links the generated tasks to a repository.
    Returns the generated questions and answer options.
    Useful for on-demand question generation for existing documents.
    """
    # TODO retrieve chunks from document model instead of search all chunks
    chunks = session.exec(select(Chunk).where(Chunk.document_id == doc_id)).all()
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No chunks found"
        )

    tasks = generate_tasks(doc_id, chunks, lm, num_tasks, task_type)

    # Save tasks and their answer options to database
    for task in tasks:
        session.add(task)
        session.flush()  # Flush to get the task ID

        # Create repository-task link if repository_id is provided
        if repository_id:
            repository_task_link = RepositoryTaskLink(
                repository_id=repository_id, task_id=task.id
            )
            session.add(repository_task_link)

    session.commit()

    return tasks


@router.post("/generate_for_multiple_documents", response_model=list[TaskRead])
async def generate_tasks_for_multiple_documents(
    request: GenerateTasksForMultipleDocumentsRequest,
    session: Session = Depends(get_db_session),
    lm: dspy.LM = Depends(get_large_llm_no_cache),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """
    Generate tasks for a number of documents and link them to the repository.
    Requires write access to the repository.
    """
    # Check repository access
    from repositories.access_control import get_repository_access

    await get_repository_access(
        request.repository_id, AccessLevel.WRITE, session, current_user
    )

    db_repository = session.get(Repository, request.repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    all_generated_tasks = []

    for document_id in request.document_ids:
        chunks = session.exec(
            select(Chunk).where(Chunk.document_id == document_id, Chunk.important)
        ).all()
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No chunks found"
            )
        tasks = generate_tasks(
            document_id, chunks, lm, request.num_tasks, request.task_type
        )

        # Save tasks and create repository-task links
        for task in tasks:
            session.add(task)
            session.flush()  # Flush to get the task ID

            # Create repository-task link
            repository_task_link = RepositoryTaskLink(
                repository_id=request.repository_id, task_id=task.id
            )
            session.add(repository_task_link)

        all_generated_tasks.extend(tasks)

    session.commit()
    return all_generated_tasks


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

    task_teacher = TaskReadTeacher(
        question=db_task.question,
        answer_options=db_task.answer_options,
        chunk=db_task.chunk,
    )

    response = evaluate_student_answer(
        task_teacher,
        request.student_answer,
        db_task.type,
        lm,
    )
    return response
