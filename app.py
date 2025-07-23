from fastapi import FastAPI
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from text_processing import extract_text_from_file

app = FastAPI()


@app.get("/", response_class=PlainTextResponse)
def read_root():
    return "Hello, World!"


@app.post("/convert_to_text", response_class=PlainTextResponse)
def convert_to_text(file: UploadFile = File(...)):
    try:
        text = extract_text_from_file(file.file, mime_type=file.content_type)
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
