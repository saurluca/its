from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from tasks.models import TaskType


# Request schemas
class TaskCreateRequest(BaseModel):
    type: TaskType
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    course_id: UUID


class TaskUpdateRequest(BaseModel):
    type: Optional[TaskType] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    course_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    chunk_id: Optional[UUID] = None


# Response schemas
class TaskResponse(BaseModel):
    id: UUID
    type: TaskType
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    course_id: UUID
    created_at: datetime
    updated_at: datetime


class TasksListResponse(BaseModel):
    tasks: List[TaskResponse]


class TaskDeleteResponse(BaseModel):
    success: bool
    id: UUID
