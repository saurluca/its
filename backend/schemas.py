from pydantic import BaseModel
from typing import List, Dict, Any


# Request schemas
class EvaluateAnswerRequest(BaseModel):
    question_id: str
    student_answer: int


class GenerateQuestionsRequest(BaseModel):
    doc_id: str
    num_questions: int = 10


# Response schemas
class HealthCheckResponse(BaseModel):
    status: str


class DocumentUploadResponse(BaseModel):
    document_id: str


class DocumentResponse(BaseModel):
    content: str


class DocumentListResponse(BaseModel):
    titles: List[str]
    ids: List[str]


class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    chunk_text: str
    metadata: Dict[str, Any]


class DocumentChunksResponse(BaseModel):
    chunks: List[ChunkResponse]


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
