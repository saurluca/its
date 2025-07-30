# File processing constants
SUPPORTED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "text/html": ".html",
    "text/plain": ".txt",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/tiff": ".tiff",
}

# Question generation constants
DEFAULT_NUM_QUESTIONS = 1
REQUIRED_ANSWER_OPTIONS = 4
MAX_TITLE_LENGTH = 100

# Response messages
HEALTH_CHECK_MESSAGE = {"status": "ok"}
ROOT_MESSAGE = "Hello, World!"

# Database constraints
MAX_CONTENT_PREVIEW_LENGTH = 1000

# Chunking constants
MIN_CHUNK_LENGTH = 420
