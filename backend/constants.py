from dotenv import load_dotenv
import os

load_dotenv()


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
DEFAULT_NUM_QUESTIONS = 3
REQUIRED_ANSWER_OPTIONS = 4
MAX_TITLE_LENGTH = 100

# Database constraints
MAX_CONTENT_PREVIEW_LENGTH = 1000

# Chunking constants
MIN_CHUNK_LENGTH = 420

# Auth constants
ACCESS_TOKEN_EXPIRE_MINUTES = 1200  # 20 hours

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
if len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be at least 32 characters long")
if not ALGORITHM:
    raise ValueError("ALGORITHM environment variable is required")
