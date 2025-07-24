import os
import psycopg
import uuid
import json
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


def save_document_to_db(text, title=None):
    # Use provided title or extract from first line
    if title is None:
        title = text.strip().split("\n", 1)[0][:255]
    else:
        title = str(title)[:255]  # Ensure it's a string and within length limit

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # check if document already exists
                cur.execute("SELECT id FROM documents WHERE title = %s;", (title,))
                row = cur.fetchone()
                if row is not None:
                    raise ValueError(f"Document with title {title} already exists")
                # save document to db
                document_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO documents (id, title, content, source_file, total_chunks)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (document_id, title, text, title, 0),
                )
                return document_id
    finally:
        conn.close()


def save_chunks_to_db(document_id, chunks):
    """
    Save chunks to the database and update the document's total_chunks count.

    Args:
        document_id (str): The UUID of the document the chunks belong to.
        chunks (list[dict]): List of chunk dictionaries with keys:
            - chunk_index: int
            - chunk_text: str
            - original_text: str
            - metadata: dict

    Returns:
        list[str]: List of chunk UUIDs that were created
    """
    conn = get_db_connection()
    chunk_ids = []

    try:
        with conn:
            with conn.cursor() as cur:
                # Insert chunks
                for chunk in chunks:
                    chunk_id = str(uuid.uuid4())
                    chunk_ids.append(chunk_id)

                    # Convert metadata to JSON string
                    metadata_json = json.dumps(chunk.get("metadata", {}))

                    cur.execute(
                        """
                        INSERT INTO chunks (id, document_id, chunk_index, chunk_text, original_text, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s);
                        """,
                        (
                            chunk_id,
                            document_id,
                            chunk["chunk_index"],
                            chunk["chunk_text"],
                            chunk.get("original_text", ""),
                            metadata_json,
                        ),
                    )

                # Update total_chunks count in documents table
                cur.execute(
                    "UPDATE documents SET total_chunks = %s WHERE id = %s;",
                    (len(chunks), document_id),
                )

    finally:
        conn.close()

    return chunk_ids


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


def save_key_points_to_db(doc_id, key_points):
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET key_points = %s WHERE id = %s;",
                    (key_points, doc_id),
                )
    finally:
        conn.close()


def get_key_points_from_db(doc_id):
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT key_points FROM documents WHERE id = %s;", (doc_id,)
                )
                row = cur.fetchone()
                return row[0]
    finally:
        conn.close()


def save_questions_to_db(doc_id, questions, answer_options):
    """
    Save a list of questions, their answer options answers to the database, linked to the given document ID.
    Each question will be inserted as a new row in the questions table.
    Args:
        doc_id (str): The UUID of the document the questions belong to.
        questions (list[str]): List of question strings.
        answer_options (list[list[str]]): List of answer options for each question (each is a list of 4 strings).
    """
    if not (len(questions) == len(answer_options)):
        raise ValueError("questions and answer_options must have the same length")
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                for q, opts in zip(questions, answer_options):
                    cur.execute(
                        """
                        INSERT INTO questions (id, question, answer_options, document_id)
                        VALUES (%s, %s, %s, %s);
                        """,
                        (str(uuid.uuid4()), q, opts, doc_id),
                    )
    finally:
        conn.close()


def get_questions_by_document_id(doc_id):
    """
    Retrieve all questions, their IDs, answer options for a given document ID.
    Returns a list of dicts: { 'id': str, 'question': str, 'answer_options': list[str] }
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, question, answer_options
                    FROM questions
                    WHERE document_id = %s;
                    """,
                    (doc_id,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "question": row[1],
                        "answer_options": row[2],
                    }
                    for row in rows
                ]
    finally:
        conn.close()


def get_question_by_id(question_id):
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT question, answer_options FROM questions WHERE id = %s;",
                    (question_id,),
                )
                row = cur.fetchone()
                return row[0], row[1]
    finally:
        conn.close()


def get_chunks_by_document_id(doc_id):
    """
    Retrieve all chunks for a given document ID.
    Returns a list of dicts with chunk information.
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, chunk_index, chunk_text, original_text, metadata
                    FROM chunks
                    WHERE document_id = %s
                    ORDER BY chunk_index;
                    """,
                    (doc_id,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": row[0],
                        "chunk_index": row[1],
                        "chunk_text": row[2],
                        "original_text": row[3],
                        "metadata": json.loads(row[4]) if row[4] else {},
                    }
                    for row in rows
                ]
    finally:
        conn.close()
