from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from typing import List, Optional, TYPE_CHECKING
from pydantic import EmailStr
from uuid import UUID, uuid4

# Import link models to avoid string reference issues
from skills.models import UserSkillLink
from tasks.models import TaskUserLink

if TYPE_CHECKING:
    from repositories.models import RepositoryAccess
    from skills.models import Skill
    from tasks.models import Task


class UserBase(SQLModel):
    email: str | None = Field(default=None, index=True)
    full_name: str | None = Field(default=None)
    disabled: bool = Field(default=False)


class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    repository_access: list["RepositoryAccess"] = Relationship(back_populates="user")
    # Skills the user is working on (via repository access)
    skills: list["Skill"] = Relationship(
        back_populates="users",
        link_model=UserSkillLink,
    )
    # Tasks the user has interacted with
    tasks: list["Task"] = Relationship(
        back_populates="users",
        link_model=TaskUserLink,
    )


class UserCreate(SQLModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: str


class UserUpdate(SQLModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None


class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class UserListResponse(SQLModel):
    users: List[UserResponse]
    total: int


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    email: str | None = None
