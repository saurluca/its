from fastapi import APIRouter, UploadFile, File, HTTPException
from documents.service import (
    get_document_titles_and_ids_from_db,
    get_document_content_from_db,
    get_chunks_by_document_id,
    save_document_to_db,
    save_chunks_to_db,
    extract_text_from_file_and_chunk,
    delete_document_from_db,
)
from documents.schemas import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunksResponse,
    DocumentDeleteResponse,
)
from exceptions import DocumentNotFoundError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/to_chunks", response_model=DocumentUploadResponse)
def document_to_chunks(file: UploadFile = File(...)) -> dict:
    """
    Converts an uploaded file to text and stores it in the database.
    Extracts text and chunks, saves them, and returns the document ID.
    """
    try:
        result = extract_text_from_file_and_chunk(
            file.file, mime_type=file.content_type
        )
        document_id = save_document_to_db(result["full_text"], title=result["name"])
        save_chunks_to_db(document_id, result["chunks"])
        return {"document_id": document_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chunks/{doc_id}", response_model=DocumentChunksResponse)
def get_document_chunks(doc_id: str):
    """
    Retrieves all text chunks for a given document ID from the database.
    Returns the chunks as a list.
    Useful for accessing segmented document content for further processing or review.
    """
    try:
        chunks = get_chunks_by_document_id(doc_id)
        return {"chunks": chunks}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=DocumentListResponse)
def get_documents():
    """
    Retrieves all document titles and their corresponding IDs from the database.
    Returns a list of titles and IDs for document selection or overview.
    """
    try:
        titles, ids = get_document_titles_and_ids_from_db()
        return {"titles": titles, "ids": ids}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: str):
    """
    Retrieves the full content of a document by its ID from the database.
    Returns the document content as a string.
    Useful for displaying or processing the original document text.
    """
    try:
        content = get_document_content_from_db(doc_id)
        return {"content": content}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
def delete_document(doc_id: str):
    """
    Deletes a document by its ID from the database.
    """
    try:
        delete_document_from_db(doc_id)
        return {"message": "Document deleted successfully"}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
