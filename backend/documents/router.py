from fastapi import APIRouter, UploadFile, File, HTTPException
from documents.service import (
    get_document_titles_and_ids_from_db,
    get_document,
    get_chunks_by_document_id,
    save_document_to_db,
    save_chunks_to_db,
    extract_text_from_file_and_chunk,
    delete_document_from_db,
    generate_document_title,
    update_document_title_in_db,
)
from documents.schemas import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunksResponse,
    DocumentDeleteResponse,
    DocumentUpdateResponse,
)
from exceptions import DocumentNotFoundError
from uuid import UUID

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=DocumentListResponse)
def get_documents_endpoint():
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
def get_document_endpoint(doc_id: str):
    """
    Retrieves the full content of a document by its ID from the database.
    Returns the document content as a string.
    Useful for displaying or processing the original document text.
    """
    try:
        response = get_document(doc_id)
        return response
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
def delete_document_endpoint(doc_id: str):
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


@router.patch("/{doc_id}", response_model=DocumentUpdateResponse)
def update_document_title_endpoint(doc_id: str, title: str):
    """
    Updates the title of a document by its ID in the database.
    """
    try:
        document_uuid = UUID(doc_id)
        update_document_title_in_db(document_uuid, title)
        return {"message": "Document title updated successfully"}
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/to_chunks", response_model=DocumentUploadResponse)
def document_to_chunks_endpoint(file: UploadFile = File(...)) -> dict:
    """
    Converts an uploaded file to text and stores it in the database.
    Extracts text and chunks, saves them, and returns the document ID.
    """
    try:
        result = extract_text_from_file_and_chunk(
            file.file, mime_type=file.content_type
        )

        title_context = "\n".join(
            [chunk["chunk_text"] for chunk in result["chunks"][:4]]
        )

        # create title for document based on first chunk
        title = generate_document_title(title_context)

        # save document and chunks to db
        document_id = save_document_to_db(result["full_text"], title=title)
        save_chunks_to_db(document_id, result["chunks"])
        return {"document_id": document_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/chunks/{doc_id}", response_model=DocumentChunksResponse)
def get_document_chunks_endpoint(doc_id: str):
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
