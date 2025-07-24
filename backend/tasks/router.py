from fastapi import APIRouter, HTTPException, status, Query
from uuid import UUID
from typing import Optional
import json

from tasks.schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TasksListResponse,
    TaskDeleteResponse,
)
from tasks.service import (
    create_task,
    get_task_by_id,
    get_all_tasks,
    get_tasks_by_course_id,
    update_task,
    delete_task,
)
from tasks.models import TaskCreate, TaskUpdate
from exceptions import DocumentNotFoundError

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=TasksListResponse)
def get_tasks(
    course_id: Optional[UUID] = Query(None, description="Filter tasks by course ID"),
):
    """
    Retrieve all tasks with optional course filtering.
    Returns a list of tasks ordered by creation date.
    """
    try:
        if course_id:
            tasks = get_tasks_by_course_id(course_id, limit=100)
        else:
            tasks = get_all_tasks(limit=100)

        task_responses = [
            TaskResponse(
                id=task.id,
                name=task.name,
                type=task.type,
                question=task.question,
                options=task.get_options_list(),
                correct_answer=task.correct_answer,
                course_id=task.course_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for task in tasks
        ]
        return TasksListResponse(tasks=task_responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(task_request: TaskCreateRequest):
    """
    Create a new task.
    Requires task details including name, type, question, options, correct answer, and course ID.
    """
    try:
        task_data = TaskCreate(
            name=task_request.name,
            type=task_request.type,
            question=task_request.question,
            options_json=None,  # Will be set after task creation
            correct_answer=task_request.correct_answer,
            course_id=task_request.course_id,
        )
        task = create_task(task_data)

        # Set options using the helper method
        if task_request.options:
            task.set_options_list(task_request.options)

        return TaskResponse(
            id=task.id,
            name=task.name,
            type=task.type,
            question=task.question,
            options=task.get_options_list(),
            correct_answer=task.correct_answer,
            course_id=task.course_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID):
    """
    Retrieve a specific task by its ID.
    Returns task details if found.
    """
    try:
        task = get_task_by_id(task_id)
        return TaskResponse(
            id=task.id,
            name=task.name,
            type=task.type,
            question=task.question,
            options=task.get_options_list(),
            correct_answer=task.correct_answer,
            course_id=task.course_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{task_id}", response_model=TaskResponse)
def update_existing_task(task_id: UUID, task_request: TaskUpdateRequest):
    """
    Update an existing task by ID.
    Only provided fields will be updated.
    """
    try:
        # Handle options conversion for update
        update_data = task_request.model_dump(exclude_unset=True)
        if "options" in update_data:
            options = update_data.pop("options")
            if options is not None:
                update_data["options_json"] = json.dumps(options)
            else:
                update_data["options_json"] = None

        task_update_data = TaskUpdate(**update_data)
        task = update_task(task_id, task_update_data)

        return TaskResponse(
            id=task.id,
            name=task.name,
            type=task.type,
            question=task.question,
            options=task.get_options_list(),
            correct_answer=task.correct_answer,
            course_id=task.course_id,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}", response_model=TaskDeleteResponse)
def delete_existing_task(task_id: UUID):
    """
    Delete a task by ID.
    Returns success status and the deleted task ID.
    """
    try:
        task = delete_task(task_id)
        return TaskDeleteResponse(success=True, id=task.id)
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
