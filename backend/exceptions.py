from fastapi import HTTPException


class DocumentNotFoundError(HTTPException):
    """Raised when a document with the given ID is not found"""

    def __init__(self, detail: str = "Document not found"):
        super().__init__(status_code=404, detail=detail)


class QuestionNotFoundError(HTTPException):
    """Raised when a question with the given ID is not found"""

    def __init__(self, detail: str = "Question not found"):
        super().__init__(status_code=404, detail=detail)


class InvalidFileFormatError(HTTPException):
    """Raised when an uploaded file has an unsupported format"""

    def __init__(self, detail: str = "Invalid file format"):
        super().__init__(status_code=400, detail=detail)


class InvalidAnswerOptionsError(HTTPException):
    """Raised when answer options don't meet the required format"""

    def __init__(self, detail: str = "Invalid answer options format"):
        super().__init__(status_code=400, detail=detail)


class DocumentProcessingError(HTTPException):
    """Raised when document processing fails"""

    def __init__(self, detail: str = "Document processing failed"):
        super().__init__(status_code=422, detail=detail)


class QuestionGenerationError(HTTPException):
    """Raised when question generation fails"""

    def __init__(self, detail: str = "Question generation failed"):
        super().__init__(status_code=422, detail=detail)
