from fastapi import APIRouter, status, Depends, HTTPException
from dependencies import get_db_session
from skills.models import (
    Skill,
    SkillCreate,
    SkillUpdate,
    SkillRead,
    UserSkillProgress,
    UserSkillLink,
    RepositorySkillLink,
)
from repositories.models import Repository, AccessLevel, RepositoryAccess
from repositories.access_control import get_repository_access
from auth.dependencies import get_current_user_from_request
from auth.models import UserResponse
from uuid import UUID
from sqlmodel import select, Session
from typing import List
from datetime import datetime

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("/", response_model=List[SkillRead])
async def get_skills(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all skills accessible to the current user via repository access."""
    # Get skills from repositories the user has access to
    accessible_skills = session.exec(
        select(Skill)
        .join(RepositorySkillLink, Skill.id == RepositorySkillLink.skill_id)
        .join(Repository, RepositorySkillLink.repository_id == Repository.id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (Repository.owner_id == current_user.id)
            | (RepositoryAccess.user_id == current_user.id)
        )
        .distinct()
    ).all()

    return accessible_skills


@router.get("/{skill_id}", response_model=SkillRead)
async def get_skill(
    skill_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get a specific skill if user has access to it via repository."""
    # Check if user has access to this skill through any repository
    skill = session.exec(
        select(Skill)
        .join(RepositorySkillLink, Skill.id == RepositorySkillLink.skill_id)
        .join(Repository, RepositorySkillLink.repository_id == Repository.id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (Skill.id == skill_id)
            & (
                (Repository.owner_id == current_user.id)
                | (RepositoryAccess.user_id == current_user.id)
            )
        )
        .distinct()
    ).first()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    return skill


@router.post("/", response_model=SkillRead, status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: SkillCreate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a new skill. Skills are global and can be shared across repositories."""
    # Check if skill with this name already exists
    existing_skill = session.exec(
        select(Skill).where(Skill.name == skill_data.name)
    ).first()

    if existing_skill:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Skill with name '{skill_data.name}' already exists",
        )

    # Create new skill
    skill = Skill(
        name=skill_data.name,
    )
    session.add(skill)
    session.commit()
    session.refresh(skill)

    return skill


@router.put("/{skill_id}", response_model=SkillRead)
async def update_skill(
    skill_id: UUID,
    skill_data: SkillUpdate,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Update a skill. Only repository owners can update skills."""
    # Get the skill
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if user has write access to any repository that uses this skill
    has_write_access = session.exec(
        select(Repository)
        .join(RepositorySkillLink, Repository.id == RepositorySkillLink.repository_id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (RepositorySkillLink.skill_id == skill_id)
            & (
                (Repository.owner_id == current_user.id)
                | (
                    (RepositoryAccess.user_id == current_user.id)
                    & (
                        RepositoryAccess.access_level.in_(
                            [AccessLevel.WRITE, AccessLevel.OWNER]
                        )
                    )
                )
            )
        )
    ).first()

    if not has_write_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this skill",
        )

    # Check if name is being changed and if it conflicts with existing skill
    if skill_data.name and skill_data.name != skill.name:
        existing_skill = session.exec(
            select(Skill).where(Skill.name == skill_data.name)
        ).first()
        if existing_skill:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Skill with name '{skill_data.name}' already exists",
            )

    # Update skill
    if skill_data.name is not None:
        skill.name = skill_data.name

    session.add(skill)
    session.commit()
    session.refresh(skill)

    return skill


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Delete a skill. Only repository owners can delete skills."""
    # Get the skill
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if user has write access to any repository that uses this skill
    has_write_access = session.exec(
        select(Repository)
        .join(RepositorySkillLink, Repository.id == RepositorySkillLink.repository_id)
        .outerjoin(RepositoryAccess, Repository.id == RepositoryAccess.repository_id)
        .where(
            (RepositorySkillLink.skill_id == skill_id)
            & (
                (Repository.owner_id == current_user.id)
                | (
                    (RepositoryAccess.user_id == current_user.id)
                    & (
                        RepositoryAccess.access_level.in_(
                            [AccessLevel.WRITE, AccessLevel.OWNER]
                        )
                    )
                )
            )
        )
    ).first()

    if not has_write_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this skill",
        )

    # Soft delete the skill
    skill.deleted_at = datetime.now()
    session.add(skill)
    session.commit()


@router.get("/user/progress", response_model=List[UserSkillProgress])
async def get_user_skill_progress(
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get the current user's progress on all skills they have access to."""
    # Get user's skill progress
    user_skills = session.exec(
        select(UserSkillLink, Skill)
        .join(Skill, UserSkillLink.skill_id == Skill.id)
        .where(UserSkillLink.user_id == current_user.id)
    ).all()

    progress_list = []
    for user_skill_link, skill in user_skills:
        progress = UserSkillProgress(
            skill_id=skill.id,
            skill_name=skill.name,
            progress=user_skill_link.progress,
            updated_at=user_skill_link.updated_at,
        )
        progress_list.append(progress)

    return progress_list


@router.get("/repository/{repository_id}", response_model=List[SkillRead])
async def get_repository_skills(
    repository_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Get all skills associated with a specific repository."""
    # Check if user has access to the repository
    await get_repository_access(repository_id, AccessLevel.READ, session, current_user)

    # Get skills for this repository
    skills = session.exec(
        select(Skill)
        .join(RepositorySkillLink, Skill.id == RepositorySkillLink.skill_id)
        .where(RepositorySkillLink.repository_id == repository_id)
    ).all()

    return skills


@router.post(
    "/repository/{repository_id}/skills/{skill_id}", status_code=status.HTTP_201_CREATED
)
async def add_skill_to_repository(
    repository_id: UUID,
    skill_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Add a skill to a repository. Requires write access to the repository."""
    # Check if user has write access to the repository
    await get_repository_access(repository_id, AccessLevel.WRITE, session, current_user)

    # Check if skill exists
    skill = session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )

    # Check if skill is already linked to repository
    existing_link = session.exec(
        select(RepositorySkillLink).where(
            (RepositorySkillLink.repository_id == repository_id)
            & (RepositorySkillLink.skill_id == skill_id)
        )
    ).first()

    if existing_link:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Skill is already linked to this repository",
        )

    # Create the link
    link = RepositorySkillLink(
        repository_id=repository_id,
        skill_id=skill_id,
    )
    session.add(link)
    session.commit()

    return {"message": "Skill added to repository successfully"}


@router.delete(
    "/repository/{repository_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_skill_from_repository(
    repository_id: UUID,
    skill_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Remove a skill from a repository. Requires write access to the repository."""
    # Check if user has write access to the repository
    await get_repository_access(repository_id, AccessLevel.WRITE, session, current_user)

    # Find and delete the link
    link = session.exec(
        select(RepositorySkillLink).where(
            (RepositorySkillLink.repository_id == repository_id)
            & (RepositorySkillLink.skill_id == skill_id)
        )
    ).first()

    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill is not linked to this repository",
        )

    session.delete(link)
    session.commit()
