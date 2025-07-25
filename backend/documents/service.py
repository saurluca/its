from sqlmodel import select
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.chunking import HybridChunker
from io import BytesIO
import dspy
from documents.models import Document, DocumentCreate, Chunk, ChunkCreate
from constants import SUPPORTED_MIME_TYPES, MAX_TITLE_LENGTH
from exceptions import DocumentNotFoundError, InvalidFileFormatError
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from utils import get_session
from sqlalchemy import desc


def save_document_to_db(text: str, title: Optional[str] = None) -> str:
    """
    Save a document to the database

    Args:
        text: The document content
        title: Optional title, if not provided, extracted from first line

    Returns:
        Document ID as string
    """
    # Use provided title or extract from first line
    if title is None:
        title = text.strip().split("\n", 1)[0][:MAX_TITLE_LENGTH]
    else:
        title = str(title)[:MAX_TITLE_LENGTH]

    with get_session() as session:
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
                chunk_metadata=None,
            )

            chunk = Chunk.model_validate(chunk_create.model_dump())
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
        DocumentNotFoundError: If no document found with the given ID
    """
    document_uuid = UUID(doc_id)

    with get_session() as session:
        statement = select(Document).where(Document.id == document_uuid)
        document = session.exec(statement).first()

        if not document:
            raise DocumentNotFoundError(f"No document found with id: {doc_id}")

        return document.content


def get_document_titles_and_ids_from_db() -> Tuple[List[str], List[str]]:
    """
    Get all document titles and IDs

    Returns:
        Tuple of (titles, ids) lists
    """
    with get_session() as session:
        statement = select(Document).order_by(desc(Document.created_at))
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
                "metadata": chunk.get_metadata_dict(),
            }
            for chunk in chunks
        ]


def extract_text_from_file_and_chunk(file_obj, mime_type=None):
    """
    Extract text from file and chunk it

    Args:
        file_obj: File-like object
        mime_type: MIME type of the file

    Returns:
        Dict with full_text, name, and chunks
    """
    assert file_obj and hasattr(file_obj, "read"), (
        "Input must be a file-like object with .read()"
    )

    # Get the name for DocumentStream
    name = getattr(file_obj, "name", None)

    # For FastAPI UploadFile, use .filename if available
    if hasattr(file_obj, "filename") and file_obj.filename:
        name = file_obj.filename

    # If still no name, create a default based on mime_type
    if not name:
        if mime_type:
            extension = SUPPORTED_MIME_TYPES.get(mime_type, ".pdf")
            name = f"uploaded_file{extension}"
        else:
            raise InvalidFileFormatError("No mime type provided")

    # Read all bytes and wrap in BytesIO for Docling
    file_obj.seek(0)
    file_bytes = file_obj.read()
    byte_stream = BytesIO(file_bytes)

    # Create DocumentStream with name and BytesIO stream
    stream = DocumentStream(name=str(name), stream=byte_stream)
    print("Converting using Docling")

    # Convert using Docling
    converter = DocumentConverter()
    result = converter.convert(stream)
    docling_doc = result.document

    print("Exporting to text")
    # Get full text for document metadata
    full_text = docling_doc.export_to_text()

    print("Chunking")
    # Use HybridChunker to split document into chunks
    chunker = HybridChunker()
    chunk_iter = chunker.chunk(dl_doc=docling_doc)

    # Collect chunks with contextualized text
    chunks = []
    for i, chunk in enumerate(chunk_iter):
        enriched_text = chunker.contextualize(chunk=chunk)

        chunks.append(
            {
                "chunk_index": i,
                "chunk_text": enriched_text,
                "metadata": {"source_file": name, "chunk_length": len(enriched_text)},
            }
        )

    return {"full_text": full_text, "name": name, "chunks": chunks}


def summarise_document(doc_id: str) -> str:
    """
    Summarize a document and save key points to database

    Args:
        doc_id: Document ID

    Returns:
        Key points summary
    """
    document = get_document_content_from_db(doc_id)

    summarizer = dspy.ChainOfThought("document -> key_points")

    response = summarizer(document=document)

    save_key_points_to_db(doc_id, response.key_points)

    return response.key_points
