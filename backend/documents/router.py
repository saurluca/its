from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
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
    get_repository_access,
)
from repositories.models import AccessLevel, RepositoryDocumentLink
from auth.dependencies import (
    get_current_user_from_request,
    get_current_user_from_websocket,
)
from auth.models import UserResponse
from uuid import UUID
from sqlmodel import select, Session
from documents.service import process_document_upload
from documents.events import document_events_manager
import os
from dotenv import load_dotenv
import logging
# Set up logging
logger = logging.getLogger(__name__)

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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    flatten_pdf: bool = Query(default=False, description="Whether to flatten the PDF"),
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    logger.info(f"Uploading and scheduling background processing for document {file.filename}...")

    if not DOCLING_SERVE_API_URL:
        raise HTTPException(
            status_code=500, detail="DOCLING_SERVE_API_URL is not configured"
        )

    # Create a placeholder document
    document = Document(
        title=file.filename,
        content="",
        source_file=file.filename,
    )
    session.add(document)
    session.commit()
    session.refresh(document)

    logger.info(f"[upload] Created document with ID: {document.id}")

    # Read file content
    file_bytes = await file.read()
    filename = file.filename
    content_type = file.content_type or "application/octet-stream"

    logger.info(f"[upload] File size: {len(file_bytes)} bytes")
    logger.info(f"[upload] Content type: {content_type}")
    logger.info(f"[upload] Scheduling async background task for document {document.id}")

    # Use FastAPI's background tasks with async function
    background_tasks.add_task(
        process_document_upload,
        document.id,
        file_bytes,
        filename,
        content_type,
        flatten_pdf,
    )

    logger.info(f"[upload] Background task scheduled successfully")

    await document_events_manager.broadcast_status(
        document.id,
        status="queued",
        message="Document queued for processing",
        payload={"uploader_id": str(current_user.id)},
    )

    return document


@router.websocket("/ws/{document_id}")
async def document_status_ws(
    websocket: WebSocket,
    document_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_websocket),
):
    document = session.get(Document, document_id)
    if not document:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    repo_links = session.exec(
        select(RepositoryDocumentLink).where(
            RepositoryDocumentLink.document_id == document_id
        )
    ).all()

    if not repo_links:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    access_granted = False
    for link in repo_links:
        try:
            await get_repository_access(
                link.repository_id, AccessLevel.READ, session, current_user
            )
            access_granted = True
            break
        except HTTPException:
            continue

    if not access_granted:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await document_events_manager.connect(document_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await document_events_manager.disconnect(document_id, websocket)


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



@router.get("/{document_id}/status")
async def get_document_status(
    document_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_document_access_dependency(AccessLevel.READ)
    ),
):
    """Get the processing status of a document."""
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    
    # Count total and important chunks
    total_chunks = session.exec(
        select(Chunk).where(Chunk.document_id == document_id)
    ).count()
    
    important_chunks = session.exec(
        select(Chunk).where(Chunk.document_id == document_id, Chunk.important)
    ).count()
    
    return {
        "id": str(document_id),
        "title": db_document.title,
        "has_content": bool(db_document.content),
        "has_summary": bool(db_document.summary),
        "total_chunks": total_chunks,
        "important_chunks": important_chunks,
        "is_processed": bool(db_document.summary and db_document.title)
    }


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
