import os
import psycopg
import uuid
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg.connect(
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
    )

def save_document_to_db(text):
    # Use the first line as the title
    title = text.strip().split("\n", 1)[0][:255]
    conn = get_db_connection()
    try:
        # check if document already exists
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM documents WHERE title = %s;", (title,))
                row = cur.fetchone()
                if row is not None:
                    raise ValueError(f"Document with title {title} already exists")
        # save document to db
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO documents (id, title, content)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (str(uuid.uuid4()), title, text),
                )
    finally:
        conn.close()


def get_document_content_from_db(doc_id):
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT content FROM documents WHERE id = %s;", (doc_id,))
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"No document found with id: {doc_id}")
                return row[0]
    finally:
        conn.close()
        

def get_document_titles_and_ids_from_db():
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, title FROM documents ORDER BY created_at DESC;")
                results = cur.fetchall()
                titles = [row[1] for row in results]
                ids = [row[0] for row in results]
        return titles, ids
    finally:
        conn.close()