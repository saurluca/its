import os
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from sqlmodel import SQLModel, Session, create_engine, select
from dotenv import load_dotenv

from models import (
    Document,
    DocumentCreate,
    Chunk,
    ChunkCreate,
    Question,
    QuestionCreate,
)

load_dotenv()


# Database configuration
def get_database_url():
    return f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"


# Create engine
engine = create_engine(get_database_url(), echo=False)


def create_db_and_tables():
    """Create database tables"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session"""
    return Session(engine)


def save_document_to_db(text: str, title: Optional[str] = None) -> str:
    """
    Save a document to the database

    Args:
        text: The document content
        title: Optional title, if not provided, extracted from first line

    Returns:
        Document ID as string

    Raises:
        ValueError: If document with same title already exists
    """
    # Use provided title or extract from first line
    if title is None:
        title = text.strip().split("\n", 1)[0][:255]
    else:
        title = str(title)[:255]  # Ensure it's a string and within length limit

    with get_session() as session:
        # Check if document already exists
        statement = select(Document).where(Document.title == title)
        existing_doc = session.exec(statement).first()
        if existing_doc:
            raise ValueError(f"Document with title {title} already exists")

        # Create new document
        document_data = DocumentCreate(
            title=title, content=text, source_file=title, total_chunks=0
        )
        document = Document.model_validate(document_data.model_dump())

        session.add(document)
        session.commit()
        session.refresh(document)

        return str(document.id)


def save_chunks_to_db(document_id: str, chunks: List[Dict[str, Any]]) -> List[str]:
    """
    Save chunks to the database and update the document's total_chunks count.

    Args:
        document_id: The UUID of the document the chunks belong to
        chunks: List of chunk dictionaries with keys:
            - chunk_index: int
            - chunk_text: str
            - original_text: str
            - metadata: dict

    Returns:
        List of chunk UUIDs that were created
    """
    chunk_ids = []
    document_uuid = UUID(document_id)

    with get_session() as session:
        # Insert chunks
        for chunk_data in chunks:
            chunk_create = ChunkCreate(
                document_id=document_uuid,
                chunk_index=chunk_data["chunk_index"],
                chunk_text=chunk_data["chunk_text"],
                original_text=chunk_data.get("original_text", ""),
                chunk_metadata=None,  # Will be set below using helper method
            )

            chunk = Chunk.model_validate(chunk_create.model_dump())

            # Set metadata using the helper method
            chunk.set_metadata_dict(chunk_data.get("metadata", {}))

            session.add(chunk)
            session.commit()
            session.refresh(chunk)

            chunk_ids.append(str(chunk.id))

        # Update total_chunks count in documents table
        statement = select(Document).where(Document.id == document_uuid)
        document = session.exec(statement).first()
        if document:
            document.total_chunks = len(chunks)
            session.add(document)
            session.commit()

    return chunk_ids


def get_document_content_from_db(doc_id: str) -> str:
    """
    Get document content by ID

    Args:
        doc_id: Document UUID as string

    Returns:
        Document content

    Raises:
        ValueError: If no document found with the given ID
    """
    document_uuid = UUID(doc_id)

    with get_session() as session:
        statement = select(Document).where(Document.id == document_uuid)
        document = session.exec(statement).first()

        if not document:
            raise ValueError(f"No document found with id: {doc_id}")

        return document.content


def get_document_titles_and_ids_from_db() -> Tuple[List[str], List[str]]:
    """
    Get all document titles and IDs

    Returns:
        Tuple of (titles, ids) lists
    """
    with get_session() as session:
        statement = select(Document).order_by(Document.created_at.desc())
        documents = session.exec(statement).all()

        titles = [doc.title for doc in documents]
        ids = [str(doc.id) for doc in documents]

        return titles, ids


def save_key_points_to_db(doc_id: str, key_points: str):
    """
    Save key points to a document

    Args:
        doc_id: Document UUID as string
        key_points: Key points text
    """
    document_uuid = UUID(doc_id)

    with get_session() as session:
        statement = select(Document).where(Document.id == document_uuid)
        document = session.exec(statement).first()

        if document:
            document.key_points = key_points
            session.add(document)
            session.commit()


def get_key_points_from_db(doc_id: str) -> Optional[str]:
    """
    Get key points from a document

    Args:
        doc_id: Document UUID as string

    Returns:
        Key points text or None
    """
    document_uuid = UUID(doc_id)

    with get_session() as session:
        statement = select(Document).where(Document.id == document_uuid)
        document = session.exec(statement).first()

        return document.key_points if document else None


def save_questions_to_db(
    doc_id: str, questions: List[str], answer_options: List[List[str]]
):
    """
    Save a list of questions and their answer options to the database, linked to the given document ID.
    Each question will be inserted as a new row in the questions table.

    Args:
        doc_id: The UUID of the document the questions belong to
        questions: List of question strings
        answer_options: List of answer options for each question (each is a list of 4 strings)
    """
    if len(questions) != len(answer_options):
        raise ValueError("questions and answer_options must have the same length")

    document_uuid = UUID(doc_id)

    with get_session() as session:
        for question_text, options in zip(questions, answer_options):
            question_create = QuestionCreate(
                question=question_text,
                answer_options="",  # Will be set below
                document_id=document_uuid,
            )

            question = Question.model_validate(question_create.model_dump())
            question.set_answer_options_list(options)

            session.add(question)

        session.commit()


def get_questions_by_document_id(doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all questions, their IDs, and answer options for a given document ID.

    Args:
        doc_id: Document UUID as string

    Returns:
        List of dicts: { 'id': str, 'question': str, 'answer_options': list[str] }
    """
    document_uuid = UUID(doc_id)

    with get_session() as session:
        statement = select(Question).where(Question.document_id == document_uuid)
        questions = session.exec(statement).all()

        return [
            {
                "id": str(question.id),
                "question": question.question,
                "answer_options": question.get_answer_options_list(),
            }
            for question in questions
        ]


def get_question_by_id(question_id: str) -> Tuple[str, List[str]]:
    """
    Get question and answer options by question ID

    Args:
        question_id: Question UUID as string

    Returns:
        Tuple of (question_text, answer_options)
    """
    question_uuid = UUID(question_id)

    with get_session() as session:
        statement = select(Question).where(Question.id == question_uuid)
        question = session.exec(statement).first()

        if not question:
            raise ValueError(f"No question found with id: {question_id}")

        return question.question, question.get_answer_options_list()


def get_chunks_by_document_id(doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all chunks for a given document ID.

    Args:
        doc_id: Document UUID as string

    Returns:
        List of dicts with chunk information
    """
    document_uuid = UUID(doc_id)

    with get_session() as session:
        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_uuid)
            .order_by(Chunk.chunk_index)
        )
        chunks = session.exec(statement).all()

        return [
            {
                "id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "original_text": chunk.original_text,
                "metadata": chunk.get_metadata_dict(),
            }
            for chunk in chunks
        ]
