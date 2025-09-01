from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_db_and_tables
from router import router
from tasks.router import router as tasks_router
from documents.router import router as documents_router
from repositories.router import router as repositories_router
from auth.router import router as auth_router
from config import LLMConfig, AppConfig
from dotenv import load_dotenv
import os
from typing import List

# Import all models to register them with SQLModel.metadata
from auth.models import User  # noqa
from documents.models import Document, Chunk  # noqa
from tasks.models import Task, AnswerOption  # noqa
from repositories.models import Repository  # noqa

load_dotenv()

app = FastAPI(
    title="ITS Backend",
    description="Backend for Intelligent Tutoring System",
    version=AppConfig.API_VERSION,
)

# Robust CORS origins parsing
origins_env = os.getenv("CORS_ORIGINS", "").strip()
if not origins_env:
    raise ValueError("CORS_ORIGINS is not set")

origins: List[str] = [o.strip() for o in origins_env.split(",") if o.strip()]
if not origins:
    raise ValueError("CORS_ORIGINS contains no valid origins")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# create_db_and_tables()

# Initialize and configure DSPy language model
LLMConfig.configure_dspy()

# Include all routers
app.include_router(router)  # health check and root endpoints
app.include_router(auth_router)
app.include_router(repositories_router)
app.include_router(tasks_router)
app.include_router(documents_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
