from pydantic import BaseModel
from typing import List


# Response schemas
class DocumentUploadResponse(BaseModel):
    document_id: str


class DocumentResponse(BaseModel):
    title: str
    content: str
    total_chunks: int


class DocumentDeleteResponse(BaseModel):
    message: str


class DocumentListResponse(BaseModel):
    titles: List[str]
    ids: List[str]


class ChunkResponse(BaseModel):
    id: str
    chunk_index: int
    chunk_text: str
    chunk_length: int


class DocumentChunksResponse(BaseModel):
    chunks: List[ChunkResponse]


class DocumentUpdateResponse(BaseModel):
    message: str
