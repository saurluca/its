import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import List, Optional
from pydantic import EmailStr


class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str | None = Field(default=None, index=True)
    full_name: str | None = Field(default=None)
    disabled: bool = Field(default=False)


class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class UserCreate(SQLModel):
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: str


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    disabled: Optional[bool] = None


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(SQLModel):
    users: List[UserResponse]
    total: int


class Token(SQLModel):
    access_token: str
    token_type: str


class TokenData(SQLModel):
    username: str | None = None
