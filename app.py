from fastapi import FastAPI
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from text_processing import extract_text_from_file
import psycopg

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


@app.get("/titles", response_class=JSONResponse)
def get_titles():
    try:
        conn = psycopg.connect(
            dbname="postgres",
            user="postgres",
            password="password",
            host="localhost",
            port=5432,
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT title FROM documents ORDER BY created_at DESC;")
                titles = [row[0] for row in cur.fetchall()]
        conn.close()
        return {"titles": titles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_class=JSONResponse)
def health_check():
    return {"status": "ok"}
