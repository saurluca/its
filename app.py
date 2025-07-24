from fastapi import FastAPI
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from text_processing import extract_text_from_file, extract_text_from_file_and_chunk
from db_utils import (
    create_db_and_tables,
    get_document_titles_and_ids_from_db,
    get_document_content_from_db,
    get_questions_by_document_id,
    get_question_by_id,
)
from teacher import evaluate_student_answer
from dotenv import load_dotenv
import dspy
from summariser import summarise_document
from question_generator import generate_questions

app = FastAPI()

load_dotenv()

# Initialize database tables
create_db_and_tables()

lm = dspy.LM("openai/gpt-4.1-nano")
dspy.configure(lm=lm)


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Hello, World!"


@app.get("/health", response_class=JSONResponse)
def health_check():
    return {"status": "ok"}


@app.post("/document_to_questions", response_class=JSONResponse)
def document_to_questions(file: UploadFile = File(...)):
    """
    Run the full pipeline:
    1. Convert file to text and save to DB (returns document_id)
    2. Summarise document (stores key points in DB)
    3. Generate questions (stores questions in DB)
    4. Return questions and related info
    """
    # Step 1: Extract text and save to DB
    document_id = extract_text_from_file(
        file.file, save_to_db=True, mime_type=file.content_type
    )

    # Step 2: Summarise document (stores key points in DB)
    key_points = summarise_document(document_id)

    # Step 3: Generate questions (stores questions in DB)
    qg_response = generate_questions(document_id)

    # Step 4: Return questions and related info
    return {
        "document_id": document_id,
        "key_points": key_points,
        "questions": qg_response.questions,
        "answer_options": qg_response.answer_options,
    }


@app.post("/convert_to_text", response_class=JSONResponse)
def convert_to_text(file: UploadFile = File(...)):
    try:
        document_id = extract_text_from_file(
            file.file, save_to_db=True, mime_type=file.content_type
        )
        return {"document_id": document_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/convert_to_chunks", response_class=JSONResponse)
def convert_to_chunks(file: UploadFile = File(...)):
    """
    Convert file to text and split into chunks for RAG system.
    Returns document_id, chunk_ids, and chunk information.
    """
    try:
        result = extract_text_from_file_and_chunk(
            file.file, save_to_db=True, mime_type=file.content_type
        )
        return {
            "document_id": result["document_id"],
            "chunk_ids": result["chunk_ids"],
            "total_chunks": len(result["chunks"]),
            "chunks_preview": [
                {
                    "chunk_index": chunk["chunk_index"],
                    "text_length": len(chunk["chunk_text"]),
                    "text_preview": chunk["chunk_text"][:200] + "..."
                    if len(chunk["chunk_text"]) > 200
                    else chunk["chunk_text"],
                    "metadata": chunk["metadata"],
                }
                for chunk in result["chunks"]
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/documents", response_class=JSONResponse)
def get_documents():
    try:
        titles, ids = get_document_titles_and_ids_from_db()
        return {"titles": titles, "ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/document/{doc_id}", response_class=JSONResponse)
def get_document(doc_id: str):
    try:
        content = get_document_content_from_db(doc_id)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/summarise_document/{doc_id}", response_class=JSONResponse)
def summarise_document_endpoint(doc_id: str):
    try:
        key_points = summarise_document(doc_id)
        return {"key_points": key_points}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/generate_questions/{doc_id}", response_class=JSONResponse)
def generate_questions_endpoint(doc_id: str):
    try:
        qg_response = generate_questions(doc_id)
        return {
            "questions": qg_response.questions,
            "answer_options": qg_response.answer_options,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/questions/{doc_id}", response_class=JSONResponse)
def get_questions(doc_id: str):
    try:
        questions = get_questions_by_document_id(doc_id)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/evaluate_answer", response_class=JSONResponse)
def evaluate_answer(question_id: str, student_answer: int):
    try:
        question, answer_options = get_question_by_id(question_id)
        feedback = evaluate_student_answer(question, answer_options, student_answer)
        return {"feedback": feedback}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
