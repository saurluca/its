from dotenv import load_dotenv
import os

load_dotenv()

# Task generation constants
DEFAULT_NUM_TASKS = 3
REQUIRED_ANSWER_OPTIONS = 4
MAX_TITLE_LENGTH = 100

# Task recommendation constants
TASKS_PER_SESSION = 6


# Database constraints
MAX_CONTENT_PREVIEW_LENGTH = 1000

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
