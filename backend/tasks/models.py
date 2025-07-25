from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import json


class TaskType(str, Enum):
    TRUE_FALSE = "true_false"
    MULTIPLE_CHOICE = "multiple_choice"
    FREE_TEXT = "free_text"


class TaskBase(SQLModel):
    name: str
    type: TaskType
    question: str
    options_json: Optional[str] = None  # JSON string representation of list
    correct_answer: str
    course_id: UUID = Field(foreign_key="course.id")


class Task(TaskBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    course: Optional["Course"] = Relationship(back_populates="tasks")

    def get_options_list(self) -> List[str]:
        """Convert options_json string to list"""
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except json.JSONDecodeError:
                return []
        return []

    def set_options_list(self, options: Optional[List[str]]):
        """Convert list to options_json string"""
        if options:
            self.options_json = json.dumps(options)
        else:
            self.options_json = None


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class TaskUpdate(SQLModel):
    name: Optional[str] = None
    type: Optional[TaskType] = None
    question: Optional[str] = None
    options_json: Optional[str] = None
    correct_answer: Optional[str] = None
    course_id: Optional[UUID] = None


# Question models for document-based questions
class QuestionBase(SQLModel):
    question: str
    answer_options: str  # JSON string representation of list
    document_id: UUID = Field(foreign_key="document.id")


class Question(QuestionBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)

    # Relationships
    document: Optional["Document"] = Relationship(back_populates="questions")

    def get_answer_options_list(self) -> List[str]:
        """Convert answer_options JSON string to list"""
        try:
            return json.loads(self.answer_options)
        except json.JSONDecodeError:
            return []

    def set_answer_options_list(self, options: List[str]):
        """Convert list to answer_options JSON string"""
        self.answer_options = json.dumps(options)


class QuestionCreate(QuestionBase):
    pass


class QuestionRead(QuestionBase):
    id: UUID
