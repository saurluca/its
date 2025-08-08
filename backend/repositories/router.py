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
    RepositoryTaskLink,
)
from documents.models import Document, DocumentResponse
from uuid import UUID
from sqlmodel import select, Session

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_model=list[RepositoryResponse])
async def get_repositories(session: Session = Depends(get_db_session)):
    db_repositories = session.exec(select(Repository)).all()

    # Create response objects with task counts
    repositories_with_task_counts = []
    for repo in db_repositories:
        # Count tasks linked to this repository
        task_count = len(
            session.exec(
                select(RepositoryTaskLink).where(
                    RepositoryTaskLink.repository_id == repo.id
                )
            ).all()
        )

        # Create response object with task count
        repo_response = RepositoryResponse.model_validate(repo)
        repo_response.task_count = task_count
        repositories_with_task_counts.append(repo_response)

    return repositories_with_task_counts


@router.get("/{repository_id}", response_model=RepositoryResponseDetail)
async def get_repository(
    repository_id: UUID, session: Session = Depends(get_db_session)
):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    repo_response = RepositoryResponseDetail.model_validate(db_repository)
    repo_response.document_ids = [doc.id for doc in db_repository.documents]
    repo_response.document_names = [doc.title for doc in db_repository.documents]
    return repo_response


@router.get("/{repository_id}/documents", response_model=list[DocumentResponse])
async def get_repository_documents(
    repository_id: UUID, session: Session = Depends(get_db_session)
):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    documents = db_repository.documents
    document_responses = []
    for doc in documents:
        doc_response = DocumentResponse.model_validate(doc)
        doc_response.repository_ids = [repo.id for repo in doc.repositories]
        document_responses.append(doc_response)

    return document_responses


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Repository)
async def create_repository(
    repository: RepositoryCreate, session: Session = Depends(get_db_session)
):
    db_repository = Repository.model_validate(repository)
    session.add(db_repository)
    session.commit()
    session.refresh(db_repository)
    return db_repository


@router.put("/{repository_id}", response_model=Repository)
async def update_repository(
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
async def delete_repository(
    repository_id: UUID, session: Session = Depends(get_db_session)
):
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
async def create_repository_document_link(
    link: RepositoryDocumentLinkCreate, session: Session = Depends(get_db_session)
):
    # Check if repository exists
    db_repository = session.get(Repository, link.repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    # Check if document exists

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
async def delete_repository_document_link(
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
