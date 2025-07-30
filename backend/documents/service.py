from sqlmodel import select
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import DocumentStream
from docling.chunking import HybridChunker
from io import BytesIO
from documents.models import Document, DocumentCreate, Chunk, ChunkCreate
from constants import SUPPORTED_MIME_TYPES, MAX_TITLE_LENGTH, MIN_CHUNK_LENGTH
from exceptions import DocumentNotFoundError, InvalidFileFormatError
from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID
from utils import get_session
from sqlalchemy import desc
import time
import dspy


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
                chunk_length=chunk_data["chunk_length"],
            )

            chunk = Chunk.model_validate(chunk_create.model_dump())

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
                "chunk_length": chunk.chunk_length,
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
    start_time = time.time()

    converter = DocumentConverter()
    result = converter.convert(stream)
    docling_doc = result.document

    if hasattr(docling_doc, "tables"):
        print(f"Document has {len(docling_doc.tables)} tables")
    else:
        print("Document does not contain any tables.")
    if hasattr(docling_doc, "images"):
        print(f"Document has {len(docling_doc.images)} images")
    else:
        print("Document does not contain any images.")

    # Get full text for document saving to db
    full_text = docling_doc.export_to_text()

    print(f"Time taken to convert: {time.time() - start_time} seconds")

    print("Chunking")
    # Use HybridChunker to split document into chunks, excluding images and documents
    chunker = HybridChunker(
        merge_peers=True,  # Merge undersized successive chunks with same headings
        include_images=False,  # Exclude images from chunks
        include_tables=False,  # Exclude tables from chunks
        include_figures=False,  # Exclude figures from chunks
        include_formulas=False,  # Exclude formulas from chunks
    )
    chunk_iter = chunker.chunk(dl_doc=docling_doc)

    # Collect chunks without contextualization, only text content
    chunks = []
    chunk_index = 0
    for chunk in chunk_iter:
        # Get text from DocChunk object
        chunk_text = chunk.text if hasattr(chunk, "text") else str(chunk)

        # Skip empty chunks or chunks that are not primarily text
        if not chunk_text or not chunk_text.strip():
            continue

        # Skip chunks that are too short (likely non-text content)
        if len(chunk_text.strip()) < 10:  # Minimum text length
            continue

        # contextualize chunk
        # chunk_text = chunker.contextualize(chunk=chunk)

        chunks.append(
            {
                "chunk_index": chunk_index,
                "chunk_text": chunk_text.strip(),
                "chunk_length": len(chunk_text.strip()),
            }
        )
        chunk_index += 1

    print(f"Time taken to chunk: {time.time() - start_time} seconds")

    if len(chunks) <= 1:
        return {"full_text": full_text, "name": name, "chunks": chunks}

    print("Post-processing chunks: merging small chunks")
    og_num_chunks = len(chunks)
    print(f"Number of chunks before post-processing: {og_num_chunks}")

    # Delete a chunk if the next chunk starts with the current chunk text (i.e. it's a duplicate, or slides adding more text)
    print("Deleting duplicate chunks")
    try:
        for i in range(len(chunks) - 2):
            chunk_text = chunks[i]["chunk_text"]
            next_chunk_text = chunks[i + 1]["chunk_text"]
            # Check if the next chunk contains the current chunk text
            if len(next_chunk_text) > len(chunk_text) and chunk_text in next_chunk_text:
                chunks.pop(i)
                i -= 1

        if len(chunks) != og_num_chunks:
            print(f"Number of removed duplicate chunks: {og_num_chunks - len(chunks)}")
            og_num_chunks = len(chunks)
    except Exception as e:
        print(f"Error deleting duplicate chunks: {e}")

    print("Merging chunks")
    # Merge chunks with neighbours until all chunks are above MIN_CHUNK_LENGTH
    i = 0
    n_merged = 0
    try:
        while i < len(chunks):
            chunk = chunks[i]

            # check if chunk is long enough
            if len(chunk["chunk_text"]) >= MIN_CHUNK_LENGTH:
                # if last chunk, we're done
                if i == len(chunks) - 1:
                    break
                # if not last chunk, move to next chunk
                i += 1
                continue

            # if first chunk, merge with next chunk
            if i == 0:
                idx_to_merge_with = i + 1
            # if last chunk, merge with prev chunk
            elif i == len(chunks) - 1:
                idx_to_merge_with = i - 1
            # if middle chunk, merge with next chunk if it's smaller
            elif len(chunks[i + 1]["chunk_text"]) < len(chunks[i - 1]["chunk_text"]):
                idx_to_merge_with = i + 1
            # else merge with prev chunk
            else:
                idx_to_merge_with = i - 1

            # merge chunk with chosen chunk
            chunks[idx_to_merge_with]["chunk_text"] += "\n\n" + chunk["chunk_text"]
            chunks.pop(i)
            n_merged += 1
    except Exception as e:
        print(f"Error merging chunks: {e}")

    # update chunk length
    for chunk in chunks:
        chunk["chunk_length"] = len(chunk["chunk_text"])

    # assert length of all chunks is greater than MIN_CHUNK_LENGTH
    count_too_short = 0
    for chunk in chunks:
        if len(chunk["chunk_text"]) < MIN_CHUNK_LENGTH:
            count_too_short += 1

    print(f"Number of chunks too short: {count_too_short}")
    print(f"Number of chunks after merging small chunks: {len(chunks)}")
    print(
        f"Number of chunks merged: {n_merged} ({n_merged / og_num_chunks * 100:.2f}%)"
    )

    return {"full_text": full_text, "name": name, "chunks": chunks}


def delete_document_from_db(doc_id: str):
    """
    Delete a document from the database
    """
    document_uuid = UUID(doc_id)
    with get_session() as session:
        statement = select(Document).where(Document.id == document_uuid)
        document = session.exec(statement).first()
        if document:
            session.delete(document)
            session.commit()
        else:
            raise DocumentNotFoundError(f"No document found with id: {doc_id}")


def generate_document_title(document_start: str) -> str:
    try:

        class DocumentTitle(dspy.Signature):
            document_start: str = dspy.InputField(
                description="The first characters of the document."
            )
            document_title: str = dspy.OutputField(
                description=f"A short title for the document based on the first characters of the document. The document is part of a lecture course. Max length: {MAX_TITLE_LENGTH} characters."
            )

        model = dspy.ChainOfThought(DocumentTitle)
        result = model(document_start=document_start)
        return result.document_title
    except Exception as e:
        print(f"Error generating document title: {e}")
        return "Untitled Document"


def update_document_title_in_db(doc_id: UUID, title: str):
    """
    Update the title of a document by its ID in the database.
    """
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError("Title is too long")

    with get_session() as session:
        statement = select(Document).where(Document.id == doc_id)
        document = session.exec(statement).first()

        if document:
            document.title = title
            session.add(document)
            session.commit()
        else:
            raise DocumentNotFoundError(f"No document found with id: {doc_id}")
