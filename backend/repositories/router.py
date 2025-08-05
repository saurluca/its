from fastapi import APIRouter, status, Depends, HTTPException
from database import get_session
from repositories.models import Repository, RepositoryCreate, RepositoryUpdate
from uuid import UUID
from sqlmodel import select, Session

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("/", response_model=list[Repository])
def get_repositories(session: Session = Depends(get_session)):
    db_repositories = session.exec(select(Repository)).all()
    return db_repositories


@router.get("/{repository_id}", response_model=Repository)
def get_repository(repository_id: UUID, session: Session = Depends(get_session)):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    return db_repository


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Repository)
def create_repository(
    repository: RepositoryCreate, session: Session = Depends(get_session)
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
    session: Session = Depends(get_session),
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
def delete_repository(repository_id: UUID, session: Session = Depends(get_session)):
    db_repository = session.get(Repository, repository_id)
    if not db_repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    session.delete(db_repository)
    session.commit()
    return {"ok": True}
