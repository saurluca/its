from dotenv import load_dotenv
import os

load_dotenv()

# Task generation constants
DEFAULT_NUM_TASKS = 3
REQUIRED_ANSWER_OPTIONS = 4
MAX_TITLE_LENGTH = 100

# Task recommendation constants
TASKS_PER_SESSION = 6

# SM-2-inspired scheduling constants (simplified)
# Partial credit weight used for free-text partial answers
SM2_PARTIAL_CREDIT = 0.5
# Boost score to ensure unseen tasks are prioritized over reviewed ones
SM2_NEW_TASK_BOOST = 1000.0
# Weight to scale recency (in days) contribution to priority
SM2_RECENCY_WEIGHT = 1.0


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
