from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from dependencies import get_db_session
from documents.models import (
    Chunk,
    Document,
    DocumentUpdate,
    DocumentResponse,
    DocumentListResponse,
)
from repositories.access_control import (
    create_document_access_dependency,
    create_chunk_access_dependency,
)
from repositories.models import AccessLevel, RepositoryDocumentLink
from auth.dependencies import (
    get_current_user_from_request,
)
from auth.models import UserResponse
from uuid import UUID
from sqlmodel import select, Session
from documents.service import process_document_upload
import os
from dotenv import load_dotenv


load_dotenv()

DOCLING_SERVE_API_URL = os.getenv("DOCLING_SERVE_API_URL")

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentListResponse])
async def get_documents(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all documents the current user has access to via repository links."""
    from repositories.models import RepositoryAccess, Repository

    # Get documents accessible through repositories the user has access to
    accessible_documents = session.exec(
        select(Document)
        .join(RepositoryDocumentLink, Document.id == RepositoryDocumentLink.document_id)
        .join(Repository, RepositoryDocumentLink.repository_id == Repository.id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (Repository.owner_id == current_user.id)
            | (RepositoryAccess.user_id == current_user.id)
        )
        .distinct()
    ).all()

    return [DocumentListResponse.model_validate(doc) for doc in accessible_documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.READ)
    ),
):
    """Get a specific document if user has read access via repository links."""
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    doc_response = DocumentResponse.model_validate(db_document)
    doc_response.repository_ids = [repo.id for repo in db_document.repositories]
    return doc_response


@router.post("/upload", response_model=Document)
async def upload_and_chunk_document(
    file: UploadFile = File(...),
    flatten_pdf: bool = Query(default=False, description="Whether to flatten the PDF"),
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """
    Upload a document and process it inline. Returns the fully processed document.
    """
    try:
        if not DOCLING_SERVE_API_URL:
            raise HTTPException(
                status_code=500, detail="DOCLING_SERVE_API_URL is not configured"
            )

        # Create initial document row
        document = Document(
            title=file.filename,
            content="",
            source_file=file.filename,
        )
        session.add(document)
        session.commit()
        session.refresh(document)

        # Read file content and process inline
        file_bytes = await file.read()
        filename = file.filename
        content_type = file.content_type or "application/octet-stream"

        # Run processing
        await process_document_upload(
            document.id,
            file_bytes,
            filename,
            content_type,
            flatten_pdf,
        )

        # Reload the document after processing
        session.refresh(document)
        return document

    except HTTPException:
        raise
    except Exception as e:
        # Log the actual error
        print(f"Error in document upload: {str(e)}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to process document: {str(e)}"
        )


# Removed websocket endpoint for simplicity


@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: UUID,
    document: DocumentUpdate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.WRITE)
    ),
):
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    document_data = document.model_dump(exclude_unset=True)
    db_document.sqlmodel_update(document_data)
    session.add(db_document)
    session.commit()
    session.refresh(db_document)
    return db_document


@router.patch("/{document_id}", response_model=Document)
async def patch_document(
    document_id: UUID,
    title: str = Query(None, description="New title for the document"),
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.WRITE)
    ),
):
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if title is not None:
        db_document.title = title
        session.add(db_document)
        session.commit()
        session.refresh(db_document)

    return db_document


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.WRITE)
    ),
):
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    session.delete(db_document)
    session.commit()
    return {"ok": True}


@router.get("/{document_id}/chunks", response_model=list[Chunk])
async def get_document_chunks(
    document_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.READ)
    ),
):
    # First check if document exists
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Query chunks by document_id
    chunks = session.exec(select(Chunk).where(Chunk.document_id == document_id)).all()
    return chunks


@router.get("/chunks/{chunk_id}", response_model=Chunk)
async def get_chunk(
    chunk_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_chunk_access_dependency(AccessLevel.READ)
    ),
):
    """Get a specific chunk if user has read access to its document's repositories."""
    db_chunk = session.get(Chunk, chunk_id)
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
        )
    return db_chunk
