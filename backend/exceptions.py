class DocumentNotFoundError(ValueError):
    """Raised when a document with the given ID is not found"""

    pass


class QuestionNotFoundError(ValueError):
    """Raised when a question with the given ID is not found"""

    pass


class InvalidFileFormatError(ValueError):
    """Raised when an uploaded file has an unsupported format"""

    pass


class InvalidAnswerOptionsError(ValueError):
    """Raised when answer options don't meet the required format"""

    pass


class DocumentProcessingError(Exception):
    """Raised when document processing fails"""

    pass


class QuestionGenerationError(Exception):
    """Raised when question generation fails"""

    pass
