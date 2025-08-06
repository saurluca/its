from fastapi import APIRouter, status, Depends, HTTPException
from dependencies import get_db_session
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
)
from uuid import UUID
from sqlmodel import select, Session


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskRead])
def get_tasks(session: Session = Depends(get_db_session)):
    db_tasks = session.exec(select(Task)).all()
    return db_tasks


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: UUID, session: Session = Depends(get_db_session)):
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return db_task


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TaskRead)
def create_task(task: TaskCreate, session: Session = Depends(get_db_session)):
    # Verify chunk exists
    db_chunk = session.get(Chunk, task.chunk_id)
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
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
def update_task(
    task_id: UUID,
    task: TaskUpdate,
    session: Session = Depends(get_db_session),
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
def delete_task(task_id: UUID, session: Session = Depends(get_db_session)):
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
def create_answer_option(
    task_id: UUID,
    answer_option: AnswerOptionCreate,
    session: Session = Depends(get_db_session),
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
def get_answer_options(
    task_id: UUID,
    session: Session = Depends(get_db_session),
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
def update_answer_option(
    task_id: UUID,
    option_id: UUID,
    answer_option_update: AnswerOptionUpdate,
    session: Session = Depends(get_db_session),
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
def delete_answer_option(
    task_id: UUID,
    option_id: UUID,
    session: Session = Depends(get_db_session),
):
    db_answer_option = session.get(AnswerOption, option_id)
    if not db_answer_option or db_answer_option.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer option not found"
        )

    session.delete(db_answer_option)
    session.commit()
    return {"ok": True}


# # Question-related endpoints
# @router.post("/document_to_questions", response_model=dict)
# def document_to_questions(
#     file: UploadFile = File(...), session: Session = Depends(get_db_session)
# ) -> dict:
#     """
#     Full pipeline endpoint for document processing.
#     1. Extracts text and chunks from the uploaded file and saves them to the database.
#     2. Summarises the document and stores key points in the database.
#     3. Generates questions and answer options from the document chunks and stores them in the database.
#     4. Returns the document ID, generated questions, and answer options.
#     This endpoint orchestrates the main workflow for document ingestion and question generation.
#     """
#     result = extract_text_from_file_and_chunk(file.file, mime_type=file.content_type)
#     document_id = save_document_to_db(result["full_text"], title=result["name"])
#     save_chunks_to_db(document_id, result["chunks"])
#     print("Generating questions")
#     tasks = generate_questions(document_id, result["chunks"])

#     # Save tasks to database
#     for task in tasks:
#         session.add(task)
#     session.commit()

#     return {
#         "document_id": document_id,
#         "tasks_created": len(tasks),
#     }


# @router.post("/generate/{doc_id}", response_model=dict)
# def generate_tasks_from_document(
#     doc_id: str,
#     num_tasks: int = DEFAULT_NUM_QUESTIONS,
#     session: Session = Depends(get_db_session),
# ):
#     """
#     Generates a specified number of questions for a given document ID.
#     Uses the document's chunks to create questions and answer options.
#     Returns the generated questions and answer options.
#     Useful for on-demand question generation for existing documents.
#     """
#     # TODO retrieve chunks from document model instead of search all chunks
#     chunks = session.exec(select(Chunk).where(Chunk.document_id == doc_id)).all()
#     if not chunks:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="No chunks found"
#         )

#     tasks = generate_questions(doc_id, chunks, num_tasks)

#     # Save tasks to database
#     for task in tasks:
#         session.add(task)
#     session.commit()

#     return {
#         "tasks_created": len(tasks),
#     }


# @router.post("/evaluate_answer/{task_id}", response_model=EvaluateAnswerResponse)
# def evaluate_answer(
#     task_id: UUID,
#     body: EvaluateAnswerRequest,
#     session: Session = Depends(get_db_session),
# ) -> EvaluateAnswerResponse:
#     """
#     Evaluate a student's answer for a specific task.
#     Returns feedback on the student's answer.
#     """
#     db_task = session.get(Task, task_id)
#     if not db_task:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
#         )

#     answer_options = db_task.get_options_list()
#     feedback = evaluate_student_answer(
#         db_task.question,
#         answer_options,
#         body.student_answer,
#         db_task.correct_answer,
#     )

#     return EvaluateAnswerResponse(feedback=feedback)
