from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import List, Optional
from pydantic import EmailStr
from uuid import UUID, uuid4


class UserBase(SQLModel):
    email: str | None = Field(default=None, index=True)
    full_name: str | None = Field(default=None)
    disabled: bool = Field(default=False)


class User(UserBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


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
