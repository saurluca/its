# from fastapi import APIRouter, status, Depends, HTTPException, UploadFile, File
# from dependencies import get_db_session
# from documents.models import Chunk
# from tasks.models import (
#     Task,
#     TaskCreate,
#     TaskUpdate,
#     EvaluateAnswerRequest,
#     EvaluateAnswerResponse,
# )
# from uuid import UUID
# from sqlmodel import select, Session
# from documents.service import (
#     extract_text_from_file_and_chunk,
#     save_document_to_db,
#     save_chunks_to_db,
# )
# from tasks.service import generate_questions, evaluate_student_answer
# from constants import DEFAULT_NUM_QUESTIONS


# router = APIRouter(prefix="/tasks", tags=["tasks"])


# @router.get("/", response_model=list[Task])
# def get_tasks(session: Session = Depends(get_db_session)):
#     db_tasks = session.exec(select(Task)).all()
#     return db_tasks


# @router.get("/{task_id}", response_model=Task)
# def get_task(task_id: UUID, session: Session = Depends(get_db_session)):
#     db_task = session.get(Task, task_id)
#     if not db_task:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
#         )
#     return db_task


# @router.post("/", status_code=status.HTTP_201_CREATED, response_model=Task)
# def create_task(task: TaskCreate, session: Session = Depends(get_db_session)):
#     db_task = Task.model_validate(task)
#     session.add(db_task)
#     session.commit()
#     session.refresh(db_task)
#     return db_task


# @router.put("/{task_id}", response_model=Task)
# def update_task(
#     task_id: UUID,
#     task: TaskUpdate,
#     session: Session = Depends(get_db_session),
# ):
#     db_task = session.get(Task, task_id)
#     if not db_task:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
#         )
#     task_data = task.model_dump(exclude_unset=True)
#     db_task.sqlmodel_update(task_data)
#     session.add(db_task)
#     session.commit()
#     session.refresh(db_task)
#     return db_task


# @router.delete("/{task_id}")
# def delete_task(task_id: UUID, session: Session = Depends(get_db_session)):
#     db_task = session.get(Task, task_id)
#     if not db_task:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
#         )
#     session.delete(db_task)
#     session.commit()
#     return {"ok": True}


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
