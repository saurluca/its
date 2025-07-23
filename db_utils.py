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


def save_questions_to_db(doc_id, questions, answer_options, correct_answers):
    """
    Save a list of questions, their answer options, and correct answers to the database, linked to the given document ID.
    Each question will be inserted as a new row in the questions table.
    Args:
        doc_id (str): The UUID of the document the questions belong to.
        questions (list[str]): List of question strings.
        answer_options (list[list[str]]): List of answer options for each question (each is a list of 4 strings).
        correct_answers (list[int]): List of indices (0-3) for the correct answer for each question.
    """
    if not (len(questions) == len(answer_options) == len(correct_answers)):
        raise ValueError(
            "questions, answer_options, and correct_answers must have the same length"
        )
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                for q, opts, correct in zip(questions, answer_options, correct_answers):
                    cur.execute(
                        """
                        INSERT INTO questions (id, question, answer_options, correct_answer, document_id)
                        VALUES (%s, %s, %s, %s, %s);
                        """,
                        (str(uuid.uuid4()), q, opts, correct, doc_id),
                    )
    finally:
        conn.close()


def get_questions_by_document_id(doc_id):
    """
    Retrieve all questions, their IDs, answer options, and correct answers for a given document ID.
    Returns a list of dicts: { 'id': str, 'question': str, 'answer_options': list[str], 'correct_answer': int }
    """
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, question, answer_options, correct_answer
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
                        "correct_answer": row[3],
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
                cur.execute("SELECT question, answer_options, correct_answer FROM questions WHERE id = %s;", (question_id,))
                row = cur.fetchone()
                return row[0], row[1], row[2]
    finally:
        conn.close()