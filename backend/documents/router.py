from click import File
from fastapi import APIRouter, status, Depends, HTTPException, UploadFile, Query
from dependencies import get_db_session
from documents.models import (
    Chunk,
    Document,
    DocumentUpdate,
    DocumentResponse,
)
from uuid import UUID
from sqlmodel import select, Session
from documents.service import extract_text_from_file_and_chunk, generate_document_title

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentResponse])
def get_documents(session: Session = Depends(get_db_session)):
    db_documents = session.exec(select(Document)).all()
    return [DocumentResponse.model_validate(doc) for doc in db_documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, session: Session = Depends(get_db_session)):
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    doc_response = DocumentResponse.model_validate(db_document)
    doc_response.repository_ids = [repo.id for repo in db_document.repositories]
    return doc_response


@router.post("/upload", response_model=Document)
def upload_and_chunk_document(
    file: UploadFile = File(...), session: Session = Depends(get_db_session)
):
    document, chunks = extract_text_from_file_and_chunk(
        file.file, mime_type=file.content_type
    )

    title_context = "\n".join([chunk.chunk_text for chunk in chunks[:4]])

    # create title for document based on first chunk
    title = generate_document_title(title_context)

    # Update document with generated title
    document.title = title
    document.source_file = file.filename
    session.add(document)
    session.commit()
    session.refresh(document)

    # Add chunks with document_id reference
    for chunk in chunks:
        chunk.document_id = document.id
        session.add(chunk)

    session.commit()
    session.refresh(document)
    return document


@router.put("/{document_id}", response_model=Document)
def update_document(
    document_id: UUID,
    document: DocumentUpdate,
    session: Session = Depends(get_db_session),
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
def patch_document(
    document_id: UUID,
    title: str = Query(None, description="New title for the document"),
    session: Session = Depends(get_db_session),
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
def delete_document(document_id: UUID, session: Session = Depends(get_db_session)):
    db_document = session.get(Document, document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    session.delete(db_document)
    session.commit()
    return {"ok": True}


@router.get("/{document_id}/chunks", response_model=list[Chunk])
def get_document_chunks(document_id: UUID, session: Session = Depends(get_db_session)):
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
def get_chunk(chunk_id: UUID, session: Session = Depends(get_db_session)):
    db_chunk = session.get(Chunk, chunk_id)
    if not db_chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
        )
    return db_chunk
