from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


# Request schemas
class CourseCreateRequest(BaseModel):
    name: str


class CourseUpdateRequest(BaseModel):
    name: Optional[str] = None


# Response schemas
class CourseResponse(BaseModel):
    id: Optional[UUID]
    name: str
    created_at: datetime
    updated_at: datetime


class CoursesListResponse(BaseModel):
    courses: List[CourseResponse]


class CourseDeleteResponse(BaseModel):
    success: bool
    id: Optional[UUID]
