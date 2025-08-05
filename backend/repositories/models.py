from sqlmodel import SQLModel, Field
from uuid import UUID, uuid4
from datetime import datetime


class RepositoryBase(SQLModel):
    name: str


class Repository(RepositoryBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.now)


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryUpdate(SQLModel):
    name: str
