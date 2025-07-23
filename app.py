from fastapi import FastAPI
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from text_processing import extract_text_from_file
from db_utils import get_document_titles_and_ids_from_db, get_document_content_from_db


app = FastAPI()


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Hello, World!"


@app.post("/convert_to_text", response_class=PlainTextResponse)
def convert_to_text(file: UploadFile = File(...)):
    try:
        text = extract_text_from_file(
            file.file, mime_type=file.content_type, save_to_db=True
        )
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/document/{doc_id}", response_class=JSONResponse)
def get_document(doc_id: str):
    try:
        content = get_document_content_from_db(doc_id)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/documents", response_class=JSONResponse)
def get_documents():
    try:
        titles, ids = get_document_titles_and_ids_from_db()
        return {"titles": titles, "ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_class=JSONResponse)
def health_check():
    return {"status": "ok"}
