from fastapi import APIRouter, status, Depends, HTTPException, Query
from dependencies import get_db_session
from units.models import (
    Unit,
    UnitCreate,
    UnitUpdate,
    UnitResponse,
    UnitListResponse,
    UnitResponseDetail,
    UnitTaskLink,
)
from repositories.models import (
    Repository,
    AccessLevel,
    RepositoryAccess,
)
from repositories.access_control import (
    create_unit_access_dependency,
    create_repository_access_dependency,
)
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse, User
from uuid import UUID
from sqlmodel import select, Session
from analytics.queries import get_unit_task_audit
from tasks.models import Task

router = APIRouter(prefix="/units", tags=["units"])

# ==========================UNIT AUDIT ENDPOINTS==============================

@router.get("/unit/{unit_id}/audit")
def unit_task_audit(
    unit_id: UUID, 
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get audit trail for unit-task assignments"""
    return get_unit_task_audit(session, unit_id, limit, offset)


@router.get("", response_model=list[UnitListResponse])
async def get_units(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all units the current user has access to via repository links."""

    # Get units accessible through repositories the user has access to
    accessible_units = session.exec(
        select(Unit)
        .join(Repository, Unit.repository_id == Repository.id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (Repository.owner_id == current_user.id)
            | (RepositoryAccess.user_id == current_user.id)
        )
        .distinct()
    ).all()

    # Sort units alphabetically by title
    accessible_units = sorted(
        accessible_units, key=lambda unit: unit.title.lower() if unit.title else ""
    )

    # Create response objects with task counts and repository info
    units_with_counts = []
    for unit in accessible_units:
        # Count tasks linked to this unit, excluding soft-deleted ones
        task_count = len(
            session.exec(
                select(Task)
                .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
                .where(UnitTaskLink.unit_id == unit.id)
                .where(Task.deleted_at.is_(None))  # Filter out soft-deleted tasks
            ).all()
        )

        # Create response object with task count and repository ID
        unit_response = UnitListResponse.model_validate(unit)
        unit_response.repository_id = unit.repository_id
        unit_response.task_count = task_count
        units_with_counts.append(unit_response)

    return units_with_counts


@router.get("/{unit_id}", response_model=UnitResponseDetail)
async def get_unit(
    unit_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_unit_access_dependency(AccessLevel.READ)
    ),
):
    """Get a specific unit if user has read access."""
    db_unit = session.get(Unit, unit_id)
    if not db_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )

    # Count tasks linked to this unit, excluding soft-deleted ones
    task_count = len(
        session.exec(
            select(Task)
            .join(UnitTaskLink, Task.id == UnitTaskLink.task_id)
            .where(UnitTaskLink.unit_id == unit_id)
            .where(Task.deleted_at.is_(None))
        ).all()
    )

    # Build detailed response explicitly to include repository_name and task info
    repository = session.get(Repository, db_unit.repository_id)
    return UnitResponseDetail(
        id=db_unit.id,
        title=db_unit.title,
        content=db_unit.content,
        created_at=db_unit.created_at,
        deleted_at=db_unit.deleted_at,
        repository_id=db_unit.repository_id,
        repository_name=repository.name if repository else "",
        task_ids=[task.id for task in db_unit.tasks],
        task_count=task_count,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UnitResponse)
async def create_unit(
    unit: UnitCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a new unit. Note: The unit must be linked to a repository after creation."""
    db_unit = Unit.model_validate(unit)
    session.add(db_unit)
    session.commit()
    session.refresh(db_unit)

    # Create response object with task count (0 for new unit)
    unit_response = UnitResponse.model_validate(db_unit)
    unit_response.repository_id = db_unit.repository_id
    unit_response.task_count = 0

    return unit_response


@router.put("/{unit_id}", response_model=UnitResponse)
async def update_unit(
    unit_id: UUID,
    unit: UnitUpdate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_unit_access_dependency(AccessLevel.WRITE)
    ),
):
    """Update a unit if user has write access."""
    db_unit = session.get(Unit, unit_id)
    if not db_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )

    unit_data = unit.model_dump(exclude_unset=True)
    db_unit.sqlmodel_update(unit_data)
    session.add(db_unit)
    session.commit()
    session.refresh(db_unit)

    # Count tasks linked to this unit
    task_count = len(
        session.exec(select(UnitTaskLink).where(UnitTaskLink.unit_id == unit_id)).all()
    )

    # Create response object with task count
    unit_response = UnitResponse.model_validate(db_unit)
    unit_response.repository_id = db_unit.repository_id
    unit_response.task_count = task_count

    return unit_response


@router.delete("/{unit_id}")
async def delete_unit(
    unit_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_unit_access_dependency(AccessLevel.WRITE)
    ),
):
    """Delete a unit if user has write access."""
    db_unit = session.get(Unit, unit_id)
    if not db_unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
        )

    session.delete(db_unit)
    session.commit()
    return {"ok": True}


@router.get("/repository/{repository_id}", response_model=list[UnitListResponse])
async def get_units_by_repository(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(
        create_repository_access_dependency(AccessLevel.READ)
    ),
):
    """Get all units for a specific repository if user has read access."""
    # Get the repository to verify it exists
    repository = session.get(Repository, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    # Get all units linked to this repository
    db_units = session.exec(
        select(Unit).where(Unit.repository_id == repository_id)
    ).all()

    # Sort units alphabetically by title
    db_units = sorted(
        db_units, key=lambda unit: unit.title.lower() if unit.title else ""
    )

    # Create response objects with task counts
    units_with_counts = []
    for unit in db_units:
        # Count tasks linked to this unit
        task_count = len(
            session.exec(
                select(UnitTaskLink).where(UnitTaskLink.unit_id == unit.id)
            ).all()
        )

        unit_response = UnitListResponse.model_validate(unit)
        unit_response.repository_id = unit.repository_id
        unit_response.task_count = task_count
        units_with_counts.append(unit_response)

    return units_with_counts
