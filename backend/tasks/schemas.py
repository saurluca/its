from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from tasks.models import TaskType


# Request schemas
class TaskCreateRequest(BaseModel):
    name: str
    type: TaskType
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    course_id: UUID


class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[TaskType] = None
    question: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    course_id: Optional[UUID] = None


# Response schemas
class TaskResponse(BaseModel):
    id: UUID
    name: str
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
