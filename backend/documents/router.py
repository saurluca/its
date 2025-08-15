from fastapi import APIRouter, status, Depends, HTTPException, UploadFile, Query, File
from dependencies import get_db_session, get_small_llm, get_large_llm
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
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse
from uuid import UUID
from sqlmodel import select, Session
from documents.service import (
    extract_text_from_file_and_chunk,
    generate_document_title,
    get_document_summary,
    filter_important_chunks,
)
from starlette.concurrency import run_in_threadpool
import dspy


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentListResponse])
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
    session: Session = Depends(get_db_session),
    large_lm: dspy.LM = Depends(get_large_llm),
    small_lm: dspy.LM = Depends(get_small_llm),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    # extract text from file and chunk
    document, chunks = await run_in_threadpool(
        extract_text_from_file_and_chunk,
        file.file,
        mime_type=file.content_type,
    )

    # set source file
    document.source_file = file.filename

    # commit to generate id, then used by chunks
    session.add(document)
    session.commit()
    session.refresh(document)

    # Add chunks with document_id reference
    for chunk in chunks:
        chunk.document_id = document.id
        session.add(chunk)

    session.commit()
    session.refresh(document)

    print("Summarising document...")
    # Get document summary
    summary_result = await run_in_threadpool(
        get_document_summary, document.content, large_lm
    )
    document.summary = summary_result.summary

    print("Generating title...")
    # create title for document based on summary
    document.title = await run_in_threadpool(
        generate_document_title, summary_result.summary, small_lm
    )
    session.add(document)

    print("Filtering important chunks...")
    # Filter important chunks using the new service function
    result = await run_in_threadpool(
        filter_important_chunks, document.chunks, summary_result, small_lm
    )

    # mark chunks as important or unimportant
    for chunk in document.chunks:
        chunk.important = chunk.chunk_index not in result["unimportant_chunks_ids"]
        session.add(chunk)
    session.commit()
    session.refresh(document)

    print(f"Marked {len(result['unimportant_chunks_ids'])} chunks as unimportant")

    return document


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
