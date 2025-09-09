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
    AccessLevel,
    RepositoryAccess,
    RepositoryAccessGrantByEmail,
)
from units.models import UnitTaskLink, Unit
from repositories.access_control import (
    create_repository_access_dependency,
    get_repository_access,
)
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse
from documents.models import Document, DocumentResponse
from uuid import UUID
from sqlmodel import select, Session
from auth.service import get_user_by_email
from units.models import UnitListResponse

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("", response_model=list[RepositoryResponse])
async def get_repositories(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all repositories the current user has access to, sorted alphabetically by name."""
    from repositories.models import RepositoryAccess

    accessible_repos = session.exec(
        select(Repository)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (Repository.owner_id == current_user.id)
            | (RepositoryAccess.user_id == current_user.id)
        )
        .distinct()
    ).all()

    # Sort repositories alphabetically by name (case-insensitive)
    accessible_repos = sorted(
        accessible_repos, key=lambda repo: repo.name.lower() if repo.name else ""
    )

    # Create response objects with access level (no task counts)
    repositories_with_access_levels = []
    for repo in accessible_repos:
        # Determine access level for the current user
        if repo.owner_id == current_user.id:
            access_level = AccessLevel.OWNER
        else:
            access_record = session.exec(
                select(RepositoryAccess).where(
                    (RepositoryAccess.repository_id == repo.id)
                    & (RepositoryAccess.user_id == current_user.id)
                )
            ).first()
            access_level = (
                access_record.access_level if access_record else AccessLevel.READ
            )

        # Create response object with access level only
        repo_response = RepositoryResponse.model_validate(repo)
        repo_response.access_level = access_level
        repositories_with_access_levels.append(repo_response)

    return repositories_with_access_levels


@router.get("/{repository_id}", response_model=RepositoryResponseDetail)
async def get_repository(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.READ)
    ),
):
    """Get a specific repository if user has read access."""
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    repo_response = RepositoryResponseDetail.model_validate(db_repository)
    repo_response.document_ids = [doc.id for doc in db_repository.documents]
    repo_response.document_names = [doc.title for doc in db_repository.documents]
    repo_response.unit_ids = [unit.id for unit in db_repository.units]
    repo_response.unit_names = [unit.title for unit in db_repository.units]
    return repo_response


@router.get("/{repository_id}/documents", response_model=list[DocumentResponse])
async def get_repository_documents(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.READ)
    ),
):
    """Get all documents in a repository if user has read access."""
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    # Sort documents alphabetically by title
    documents = sorted(
        db_repository.documents, key=lambda doc: doc.title.lower() if doc.title else ""
    )
    document_responses = []
    for doc in documents:
        doc_response = DocumentResponse.model_validate(doc)
        doc_response.repository_ids = [repo.id for repo in doc.repositories]
        document_responses.append(doc_response)

    return document_responses


@router.get("/{repository_id}/units", response_model=list)
async def get_repository_units(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.READ)
    ),
):
    """Get all units in a repository if user has read access."""

    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    # Sort units alphabetically by title
    units = sorted(
        db_repository.units, key=lambda unit: unit.title.lower() if unit.title else ""
    )
    unit_responses = []
    for unit in units:
        # Count tasks for each unit
        task_count = len(
            session.exec(
                select(UnitTaskLink).where(UnitTaskLink.unit_id == unit.id)
            ).all()
        )

        unit_response = UnitListResponse.model_validate(unit)
        unit_response.repository_ids = [repo.id for repo in unit.repositories]
        unit_response.task_count = task_count
        unit_responses.append(unit_response)

    return unit_responses


@router.post("", status_code=status.HTTP_201_CREATED, response_model=RepositoryResponse)
async def create_repository(
    repository: RepositoryCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a new repository. The creating user becomes the owner."""
    db_repository = Repository.model_validate(repository)
    db_repository.owner_id = current_user.id  # Set the current user as owner
    session.add(db_repository)
    session.commit()
    session.refresh(db_repository)

    # Create response object with task count (0 for new repository)
    repo_response = RepositoryResponse.model_validate(db_repository)
    repo_response.access_level = AccessLevel.OWNER
    return repo_response


@router.put("/{repository_id}", response_model=RepositoryResponse)
async def update_repository(
    repository_id: UUID,
    repository: RepositoryUpdate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.WRITE)
    ),
):
    """Update a repository if user has write access."""
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

    # Create response object without task count
    repo_response = RepositoryResponse.model_validate(db_repository)
    repo_response.access_level = (
        AccessLevel.OWNER
        if db_repository.owner_id == current_user.id
        else AccessLevel.WRITE
    )
    return repo_response


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.OWNER)
    ),
):
    """Delete a repository if user is the owner."""
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
    link: RepositoryDocumentLinkCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a document-repository link if user has write access to the repository."""
    # Check repository access
    await get_repository_access(
        link.repository_id, AccessLevel.WRITE, session, current_user
    )

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
    repository_id: UUID,
    document_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.WRITE)
    ),
):
    """Delete a document-repository link if user has write access to the repository."""
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


@router.post(
    "/{repository_id}/access",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def grant_repository_access_by_email(
    repository_id: UUID,
    grant: RepositoryAccessGrantByEmail,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.WRITE)
    ),
):
    """Grant read/write access to a repository by user email.

    Fails silently (204) if the user email does not exist, to avoid user enumeration.
    Only READ or WRITE can be granted via this endpoint.
    """
    # Validate requested access level
    if grant.access_level not in (AccessLevel.READ, AccessLevel.WRITE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid access level. Only 'read' or 'write' allowed.",
        )

    # Resolve user by email; fail silently if not found
    target_user = await get_user_by_email(grant.email, session)
    if not target_user:
        return None

    # Avoid creating redundant access for repository owner
    repository = session.get(Repository, repository_id)
    if repository and repository.owner_id == target_user.id:
        return None

    # Upsert RepositoryAccess
    existing = session.exec(
        select(RepositoryAccess).where(
            (RepositoryAccess.repository_id == repository_id)
            & (RepositoryAccess.user_id == target_user.id)
        )
    ).first()

    if existing:
        existing.access_level = grant.access_level
        session.add(existing)
    else:
        new_access = RepositoryAccess(
            repository_id=repository_id,
            user_id=target_user.id,
            access_level=grant.access_level,
        )
        session.add(new_access)

    session.commit()
    return None
