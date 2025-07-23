from fastapi import FastAPI
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from text_processing import extract_text_from_file
from db_utils import (
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

lm = dspy.LM("openai/gpt-4.1-nano")
dspy.configure(lm=lm)


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Hello, World!"


@app.get("/health", response_class=JSONResponse)
def health_check():
    return {"status": "ok"}


@app.post("/convert_to_text", response_class=JSONResponse)
def convert_to_text(file: UploadFile = File(...)):
    try:
        document_id = extract_text_from_file(
            file.file, save_to_db=True, mime_type=file.content_type
        )
        return {"document_id": document_id}
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
            "correct_answers": qg_response.correct_answers,
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
        question, answer_options, correct_answer = get_question_by_id(question_id)
        feedback = evaluate_student_answer(
            question, answer_options, correct_answer, student_answer
        )
        return {"feedback": feedback}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
