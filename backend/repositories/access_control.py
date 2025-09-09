"""
Repository access control dependencies for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session, select
from typing import Callable
from uuid import UUID

from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse
from dependencies import get_db_session
from repositories.models import (
    RepositoryAccess,
    AccessLevel,
    Repository,
    RepositoryDocumentLink,
)
from documents.models import Document, Chunk
from tasks.models import Task
from units.models import Unit, UnitTaskLink


async def get_repository_access(
    repository_id: UUID,
    required_access: AccessLevel,
    session: Session,
    current_user: UserResponse,
) -> bool:
    """
    Check if the current user has the required access level to a specific repository.

    Args:
        repository_id: The repository ID to check access for
        required_access: The minimum access level required (READ, WRITE, OWNER)
        session: Database session
        current_user: Current authenticated user

    Returns:
        bool: True if user has access, raises HTTPException if not

    Raises:
        HTTPException: 404 if repository not found, 403 if access denied
    """
    # Check if repository exists
    repository = session.get(Repository, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    # Check if user is the owner of the repository
    if repository.owner_id == current_user.id:
        return True

    # Query user's access to this repository
    access_record = session.exec(
        select(RepositoryAccess).where(
            RepositoryAccess.user_id == current_user.id,
            RepositoryAccess.repository_id == repository_id,
        )
    ).first()

    if not access_record:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: No access to this repository",
        )

    # Define access level hierarchy
    access_hierarchy = {AccessLevel.READ: 1, AccessLevel.WRITE: 2, AccessLevel.OWNER: 3}

    user_access_level = access_hierarchy.get(access_record.access_level, 0)
    required_access_level = access_hierarchy.get(required_access, 1)

    if user_access_level < required_access_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: {required_access.value} access required",
        )

    return True


def create_repository_access_dependency(
    required_access: AccessLevel = AccessLevel.READ,
    repository_id_param: str = "repository_id",
) -> Callable:
    """
    Create a FastAPI dependency for direct repository access checking.

    Args:
        required_access: Minimum access level required (default: READ)
        repository_id_param: Name of the path parameter containing repository_id

    Returns:
        FastAPI dependency function
    """

    async def check_repository_access(
        request: Request,
        session: Session = Depends(get_db_session),
        current_user: UserResponse = Depends(get_current_user_from_request),
    ) -> UserResponse:
        # Extract repository_id from path parameters
        repository_id = request.path_params.get(repository_id_param)
        if not repository_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {repository_id_param} in path",
            )

        try:
            repository_uuid = UUID(repository_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid repository ID format",
            )

        await get_repository_access(
            repository_uuid, required_access, session, current_user
        )
        return current_user

    return check_repository_access


def create_document_access_dependency(
    required_access: AccessLevel = AccessLevel.READ,
    document_id_param: str = "document_id",
) -> Callable:
    """
    Create a FastAPI dependency for document access checking via repository relationships.

    Args:
        required_access: Minimum access level required (default: READ)
        document_id_param: Name of the path parameter containing document_id

    Returns:
        FastAPI dependency function
    """

    async def check_document_access(
        request: Request,
        session: Session = Depends(get_db_session),
        current_user: UserResponse = Depends(get_current_user_from_request),
    ) -> UserResponse:
        # Extract document_id from path parameters
        document_id = request.path_params.get(document_id_param)
        if not document_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {document_id_param} in path",
            )

        try:
            document_uuid = UUID(document_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format",
            )

        # Get document to check if it exists
        document = session.get(Document, document_uuid)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        # Get all repositories linked to this document
        repository_links = session.exec(
            select(RepositoryDocumentLink).where(
                RepositoryDocumentLink.document_id == document_uuid
            )
        ).all()

        if not repository_links:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Document not linked to any repository",
            )

        # Check access to at least one repository linked to this document
        access_granted = False
        for link in repository_links:
            try:
                await get_repository_access(
                    link.repository_id, required_access, session, current_user
                )
                access_granted = True
                break
            except HTTPException:
                continue

        if not access_granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No access to repositories containing this document",
            )

        return current_user

    return check_document_access


def create_task_access_dependency(
    required_access: AccessLevel = AccessLevel.READ, task_id_param: str = "task_id"
) -> Callable:
    """
    Create a FastAPI dependency for task access checking via repository relationships.

    Args:
        required_access: Minimum access level required (default: READ)
        task_id_param: Name of the path parameter containing task_id

    Returns:
        FastAPI dependency function
    """

    async def check_task_access(
        request: Request,
        session: Session = Depends(get_db_session),
        current_user: UserResponse = Depends(get_current_user_from_request),
    ) -> UserResponse:
        # Extract task_id from path parameters
        task_id = request.path_params.get(task_id_param)
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {task_id_param} in path",
            )

        try:
            task_uuid = UUID(task_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid task ID format"
            )

        # Get task to check if it exists
        task = session.get(Task, task_uuid)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
            )

        # Get all repositories linked to this task through units
        # Repository -> Unit -> Task relationship
        repository_ids = session.exec(
            select(Unit.repository_id)
            .join(UnitTaskLink, Unit.id == UnitTaskLink.unit_id)
            .where(UnitTaskLink.task_id == task_uuid)
        ).all()

        if not repository_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Task not linked to any repository through units",
            )

        # Check access to at least one repository linked to this task through units
        access_granted = False
        for repository_id in repository_ids:
            try:
                await get_repository_access(
                    repository_id, required_access, session, current_user
                )
                access_granted = True
                break
            except HTTPException:
                continue

        if not access_granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No access to repositories containing this task",
            )

        return current_user

    return check_task_access


def create_chunk_access_dependency(
    required_access: AccessLevel = AccessLevel.READ, chunk_id_param: str = "chunk_id"
) -> Callable:
    """
    Create a FastAPI dependency for chunk access checking via document-repository relationships.

    Args:
        required_access: Minimum access level required (default: READ)
        chunk_id_param: Name of the path parameter containing chunk_id

    Returns:
        FastAPI dependency function
    """

    async def check_chunk_access(
        request: Request,
        session: Session = Depends(get_db_session),
        current_user: UserResponse = Depends(get_current_user_from_request),
    ) -> UserResponse:
        # Extract chunk_id from path parameters
        chunk_id = request.path_params.get(chunk_id_param)
        if not chunk_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {chunk_id_param} in path",
            )

        try:
            chunk_uuid = UUID(chunk_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid chunk ID format",
            )

        # Get chunk to check if it exists
        chunk = session.get(Chunk, chunk_uuid)
        if not chunk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found"
            )

        # Get all repositories linked to this chunk's document
        repository_links = session.exec(
            select(RepositoryDocumentLink).where(
                RepositoryDocumentLink.document_id == chunk.document_id
            )
        ).all()

        if not repository_links:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Chunk's document not linked to any repository",
            )

        # Check access to at least one repository linked to this chunk's document
        access_granted = False
        for link in repository_links:
            try:
                await get_repository_access(
                    link.repository_id, required_access, session, current_user
                )
                access_granted = True
                break
            except HTTPException:
                continue

        if not access_granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No access to repositories containing this chunk's document",
            )

        return current_user

    return check_chunk_access


def create_unit_access_dependency(
    required_access: AccessLevel = AccessLevel.READ, unit_id_param: str = "unit_id"
) -> Callable:
    """
    Create a FastAPI dependency for unit access checking via repository relationships.

    Args:
        required_access: Minimum access level required (default: READ)
        unit_id_param: Name of the path parameter containing unit_id

    Returns:
        FastAPI dependency function
    """

    async def check_unit_access(
        request: Request,
        session: Session = Depends(get_db_session),
        current_user: UserResponse = Depends(get_current_user_from_request),
    ) -> UserResponse:
        # Extract unit_id from path parameters
        unit_id = request.path_params.get(unit_id_param)
        if not unit_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {unit_id_param} in path",
            )

        try:
            unit_uuid = UUID(unit_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid unit ID format",
            )

        # Get unit to check if it exists
        unit = session.get(Unit, unit_uuid)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found"
            )

        # Check access to the repository linked to this unit
        try:
            await get_repository_access(
                unit.repository_id, required_access, session, current_user
            )
        except HTTPException:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: No access to repository containing this unit",
            )

        return current_user

    return check_unit_access


# Pre-configured dependencies for common use cases
require_repository_read = create_repository_access_dependency(AccessLevel.READ)
require_repository_write = create_repository_access_dependency(AccessLevel.WRITE)
require_repository_owner = create_repository_access_dependency(AccessLevel.OWNER)

require_document_read = create_document_access_dependency(AccessLevel.READ)
require_document_write = create_document_access_dependency(AccessLevel.WRITE)

require_task_read = create_task_access_dependency(AccessLevel.READ)
require_task_write = create_task_access_dependency(AccessLevel.WRITE)

require_chunk_read = create_chunk_access_dependency(AccessLevel.READ)
require_chunk_write = create_chunk_access_dependency(AccessLevel.WRITE)

require_unit_read = create_unit_access_dependency(AccessLevel.READ)
require_unit_write = create_unit_access_dependency(AccessLevel.WRITE)
