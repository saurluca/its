from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
import time

from utils import (
    get_document_titles_and_ids_from_db,
    get_document_content_from_db,
    get_questions_by_document_id,
    get_question_by_id,
    save_document_to_db,
    save_chunks_to_db,
    save_questions_to_db,
    get_chunks_by_document_id,
    extract_text_from_file_and_chunk,
)
from service import generate_questions, evaluate_student_answer
from schemas import (
    HealthCheckResponse,
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunksResponse,
    QuestionsResponse,
    GeneratedQuestionsResponse,
    DocumentToQuestionsResponse,
    EvaluateAnswerResponse,
)
from constants import ROOT_MESSAGE, HEALTH_CHECK_MESSAGE, DEFAULT_NUM_QUESTIONS
from exceptions import DocumentNotFoundError, QuestionNotFoundError

router = APIRouter()


@router.get("/", response_class=PlainTextResponse)
def read_root():
    """
    Root endpoint for the API.
    Returns a simple greeting message to verify the API is running.
    """
    return ROOT_MESSAGE


@router.get("/health", response_model=HealthCheckResponse)
def health_check():
    """
    Health check endpoint.
    Returns a JSON object indicating the service status.
    Useful for monitoring and deployment checks.
    """
    return HEALTH_CHECK_MESSAGE


@router.post("/document_to_questions", response_model=DocumentToQuestionsResponse)
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
        questions, answer_options = generate_questions(document_id, result["chunks"])
        print("Saving questions")
        # Step 2.1: Save questions to database
        save_questions_to_db(document_id, questions, answer_options)
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


@router.post("/document_to_chunks", response_model=DocumentUploadResponse)
def document_to_chunks(file: UploadFile = File(...)) -> dict:
    """
    Converts an uploaded file to text and stores it in the database.
    Extracts text and chunks, saves them, and returns the document ID.
    """
    try:
        result = extract_text_from_file_and_chunk(
            file.file, mime_type=file.content_type
        )
        document_id = save_document_to_db(result["full_text"], title=result["name"])
        save_chunks_to_db(document_id, result["chunks"])
        return {"document_id": document_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/document_chunks/{doc_id}", response_model=DocumentChunksResponse)
def get_document_chunks(doc_id: str):
    """
    Retrieves all text chunks for a given document ID from the database.
    Returns the chunks as a list.
    Useful for accessing segmented document content for further processing or review.
    """
    try:
        chunks = get_chunks_by_document_id(doc_id)
        return {"chunks": chunks}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
def get_documents():
    """
    Retrieves all document titles and their corresponding IDs from the database.
    Returns a list of titles and IDs for document selection or overview.
    """
    try:
        titles, ids = get_document_titles_and_ids_from_db()
        return {"titles": titles, "ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str):
    """
    Retrieves the full content of a document by its ID from the database.
    Returns the document content as a string.
    Useful for displaying or processing the original document text.
    """
    try:
        content = get_document_content_from_db(doc_id)
        return {"content": content}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/generate_questions/{doc_id}", response_model=GeneratedQuestionsResponse)
def generate_questions_endpoint(
    doc_id: str, num_questions: int = DEFAULT_NUM_QUESTIONS
):
    """
    Generates a specified number of questions for a given document ID.
    Uses the document's chunks to create questions and answer options.
    Returns the generated questions and answer options.
    Useful for on-demand question generation for existing documents.
    """
    try:
        chunks = get_chunks_by_document_id(doc_id)
        questions, answer_options = generate_questions(doc_id, chunks, num_questions)
        return {
            "questions": questions,
            "answer_options": answer_options,
        }
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/questions/{doc_id}", response_model=QuestionsResponse)
def get_questions(doc_id: str):
    """
    Retrieves all questions associated with a given document ID from the database.
    Returns the questions as a list.
    Useful for reviewing or displaying generated questions for a document.
    """
    try:
        questions = get_questions_by_document_id(doc_id)
        return {"questions": questions}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/evaluate_answer", response_model=EvaluateAnswerResponse)
def evaluate_answer(question_id: str, student_answer: int):
    """
    Evaluates a student's answer to a specific question.
    Retrieves the question and answer options by question ID, then uses the evaluation logic to provide feedback.
    Returns feedback on the student's answer.
    Useful for automated grading or feedback in quiz applications.
    """
    try:
        question, answer_options = get_question_by_id(question_id)
        feedback = evaluate_student_answer(question, answer_options, student_answer)
        return {"feedback": feedback}
    except QuestionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
