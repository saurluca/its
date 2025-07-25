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


# Question-related schemas
class EvaluateAnswerRequest(BaseModel):
    question_id: str
    student_answer: int


class GenerateQuestionsRequest(BaseModel):
    doc_id: str
    num_questions: int = 10


class QuestionResponse(BaseModel):
    id: str
    question: str
    answer_options: List[str]


class QuestionsResponse(BaseModel):
    questions: List[QuestionResponse]


class GeneratedQuestionsResponse(BaseModel):
    questions: List[str]
    answer_options: List[List[str]]


class DocumentToQuestionsResponse(BaseModel):
    document_id: str
    questions: List[str]
    answer_options: List[List[str]]


class EvaluateAnswerResponse(BaseModel):
    feedback: str
