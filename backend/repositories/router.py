from fastapi import APIRouter, status, Depends, HTTPException
from dependencies import get_db_session
from repositories.models import (
    Repository,
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryDocumentLink,
    RepositoryDocumentLinkCreate,
    RepositoryDocumentLinkResponse,
    RepositoryResponseDetail,
)
from uuid import UUID
from sqlmodel import select, Session

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_model=list[RepositoryResponse])
def get_repositories(session: Session = Depends(get_db_session)):
    db_repositories = session.exec(select(Repository)).all()
    return db_repositories


@router.get("/{repository_id}", response_model=RepositoryResponseDetail)
def get_repository(repository_id: UUID, session: Session = Depends(get_db_session)):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    repo_response = RepositoryResponseDetail.model_validate(db_repository)
    repo_response.document_ids = [doc.id for doc in db_repository.documents]
    repo_response.document_names = [doc.title for doc in db_repository.documents]
    return repo_response


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Repository)
def create_repository(
    repository: RepositoryCreate, session: Session = Depends(get_db_session)
):
    db_repository = Repository.model_validate(repository)
    session.add(db_repository)
    session.commit()
    session.refresh(db_repository)
    return db_repository


@router.put("/{repository_id}", response_model=Repository)
def update_repository(
    repository_id: UUID,
    repository: RepositoryUpdate,
    session: Session = Depends(get_db_session),
):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    repository_data = repository.model_dump(exclude_unset=True)
    db_repository.sqlmodel_update(repository_data)
    session.add(db_repository)
    session.commit()
    session.refresh(db_repository)
    return db_repository


@router.delete("/{repository_id}")
def delete_repository(repository_id: UUID, session: Session = Depends(get_db_session)):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    session.delete(db_repository)
    session.commit()
    return {"ok": True}


@router.post(
    "/links",
    status_code=status.HTTP_201_CREATED,
    response_model=RepositoryDocumentLinkResponse,
)
def create_repository_document_link(
    link: RepositoryDocumentLinkCreate, session: Session = Depends(get_db_session)
):
    # Check if repository exists
    db_repository = session.get(Repository, link.repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    # Check if document exists
    from documents.models import Document

    db_document = session.get(Document, link.document_id)
    if not db_document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Check if link already exists
    existing_link = session.exec(
        select(RepositoryDocumentLink).where(
            RepositoryDocumentLink.repository_id == link.repository_id,
            RepositoryDocumentLink.document_id == link.document_id,
        )
    ).first()

    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository-Document link already exists",
        )

    # Create the link
    db_link = RepositoryDocumentLink(
        repository_id=link.repository_id, document_id=link.document_id
    )
    session.add(db_link)
    session.commit()
    session.refresh(db_link)

    return RepositoryDocumentLinkResponse(
        repository_id=db_link.repository_id,
        document_id=db_link.document_id,
        created_at=db_link.created_at,
    )


@router.delete("/links/{repository_id}/{document_id}")
def delete_repository_document_link(
    repository_id: UUID, document_id: UUID, session: Session = Depends(get_db_session)
):
    # Check if link exists
    db_link = session.exec(
        select(RepositoryDocumentLink).where(
            RepositoryDocumentLink.repository_id == repository_id,
            RepositoryDocumentLink.document_id == document_id,
        )
    ).first()

    if not db_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository-Document link not found",
        )

    session.delete(db_link)
    session.commit()
    return {"ok": True}
