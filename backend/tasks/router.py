from fastapi import APIRouter, HTTPException, status, Query, UploadFile, File
from uuid import UUID
from typing import Optional
import json
import time

from tasks.schemas import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TasksListResponse,
    TaskDeleteResponse,
    EvaluateAnswerRequest,
)
from tasks.service import (
    create_task,
    get_task_by_id,
    get_all_tasks,
    get_tasks_by_course_id,
    update_task,
    delete_task,
    generate_questions,
    evaluate_student_answer,
    save_questions_to_db,
    get_question_by_id,
)
from tasks.models import TaskCreate, TaskUpdate, Task
from documents.service import (
    save_document_to_db,
    save_chunks_to_db,
    extract_text_from_file_and_chunk,
    get_chunks_by_document_id,
)
from exceptions import DocumentNotFoundError
from constants import DEFAULT_NUM_QUESTIONS

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
                question=task.question,
                type=task.type,
                options=task.get_options_list(),
                correct_answer=task.correct_answer,
                course_id=task.course_id,
                document_id=task.document_id,
                chunk_id=task.chunk_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for task in tasks
        ]
        return TasksListResponse(tasks=task_responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{document_id}", response_model=TasksListResponse)
def get_tasks_by_document_id_endpoint(document_id: str):
    """
    Retrieve all tasks associated with a given document ID.
    """
    try:
        # Get the actual Task objects from the database
        document_uuid = UUID(document_id)
        from tasks.service import get_session
        from sqlmodel import select

        with get_session() as session:
            statement = select(Task).where(Task.document_id == document_uuid)
            tasks = session.exec(statement).all()

        task_responses = [
            TaskResponse(
                id=task.id,
                question=task.question,
                type=task.type,
                options=task.get_options_list(),
                correct_answer=task.correct_answer,
                course_id=task.course_id,
                document_id=task.document_id,
                chunk_id=task.chunk_id,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            for task in tasks
        ]
        return TasksListResponse(tasks=task_responses)
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_new_task(task_request: TaskCreateRequest):
    """
    Create a new task.
    Requires task details including question, type, options, correct answer, and course ID.
    """
    try:
        task_data = TaskCreate(
            question=task_request.question,
            type=task_request.type,
            options_json=None,  # Will be set after task creation
            correct_answer=task_request.correct_answer,
            course_id=task_request.course_id,
        )
        task = create_task(task_data)

        # Set options using the helper method
        if task_request.options:
            task.set_options_list(task_request.options)
            # Persist the options to the database
            task = update_task(task.id, TaskUpdate(options_json=task.options_json))

        return TaskResponse(
            id=task.id,
            question=task.question,
            type=task.type,
            options=task.get_options_list(),
            correct_answer=task.correct_answer,
            course_id=task.course_id,
            document_id=task.document_id,
            chunk_id=task.chunk_id,
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
            question=task.question,
            type=task.type,
            options=task.get_options_list(),
            correct_answer=task.correct_answer,
            course_id=task.course_id,
            document_id=task.document_id,
            chunk_id=task.chunk_id,
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
            question=task.question,
            type=task.type,
            options=task.get_options_list(),
            correct_answer=task.correct_answer,
            course_id=task.course_id,
            document_id=task.document_id,
            chunk_id=task.chunk_id,
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


# Question-related endpoints
@router.post("/document_to_questions", response_model=dict)
def document_to_questions(file: UploadFile = File(...)) -> dict:
    """
    Full pipeline endpoint for document processing.
    1. Extracts text and chunks from the uploaded file and saves them to the database.
    2. Summarises the document and stores key points in the database.
    3. Generates questions and answer options from the document chunks and stores them in the database.
    4. Returns the document ID, generated questions, and answer options.
    This endpoint orchestrates the main workflow for document ingestion and question generation.
    """
    try:
        start_time = time.time()
        # Step 1: Extract text, chunks and save to db
        print("Extracting text and chunks")
        result = extract_text_from_file_and_chunk(
            file.file, mime_type=file.content_type
        )
        print("Saving document metadata and chunks")
        # Step 1.1: Save document metadata and get document_id
        document_id = save_document_to_db(result["full_text"], title=result["name"])
        # Step 1.2: Save chunks to database
        save_chunks_to_db(document_id, result["chunks"])
        print("Generating questions")
        # Step 2: Generate questions (stores questions in DB)
        questions, answer_options, chunk_ids = generate_questions(
            document_id, result["chunks"]
        )
        print("Saving questions")
        # Step 2.1: Save questions to database
        save_questions_to_db(document_id, questions, answer_options, chunk_ids)
        end_time = time.time()
        print(f"Time taken: {end_time - start_time} seconds")
        # Step 3: Return questions and related info
        return {
            "document_id": document_id,
            "questions": questions,
            "answer_options": answer_options,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate/{doc_id}", response_model=dict)
def generate_tasks_from_document(doc_id: str, num_tasks: int = DEFAULT_NUM_QUESTIONS):
    """
    Generates a specified number of questions for a given document ID.
    Uses the document's chunks to create questions and answer options.
    Returns the generated questions and answer options.
    Useful for on-demand question generation for existing documents.
    """
    try:
        chunks = get_chunks_by_document_id(doc_id)
        questions, answer_options, chunk_ids = generate_questions(
            doc_id, chunks, num_tasks
        )
        save_questions_to_db(doc_id, questions, answer_options, chunk_ids)
        return {
            "questions": questions,
            "answer_options": answer_options,
        }
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/evaluate_answer/{question_id}", response_model=dict)
def evaluate_answer(question_id: UUID, body: EvaluateAnswerRequest) -> dict:
    student_answer = body.student_answer
    try:
        question, answer_options = get_question_by_id(question_id)
        correct_answer = answer_options[0]
        feedback = evaluate_student_answer(
            question, answer_options, student_answer, correct_answer
        )
        return {"feedback": feedback}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
