from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from router import router
from tasks.router import router as tasks_router
from documents.router import router as documents_router
from repositories.router import router as repositories_router
from auth.router import router as auth_router
from skills.router import router as skills_router
from reports.router import router as reports_router
from reports.models import Report  # noqa: F401 - ensure model is registered
from units.router import router as units_router
from config import LLMConfig, AppConfig
from database import create_db_and_tables, wait_for_database
from dependencies import get_database_engine
from dotenv import load_dotenv
import os
from typing import List

# Import all models to register them with SQLModel.metadata
from auth.models import User  # noqa
from documents.models import Document, Chunk  # noqa
from tasks.models import Task, AnswerOption  # noqa
from repositories.models import Repository  # noqa
from skills.models import Skill, UserSkillLink, RepositorySkillLink  # noqa
from sqlmodel import SQLModel

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: wait for database and create tables
    print("Starting application...")

    # Wait for database to be ready
    if not wait_for_database():
        raise RuntimeError("Database is not ready")

    # Create database tables
    create_db_and_tables()
    print("Database tables created successfully")

    yield

    # Shutdown: (add any cleanup logic here if needed)
    print("Shutting down application...")


app = FastAPI(
    title="ITS Backend",
    description="Backend for Intelligent Tutoring System",
    version=AppConfig.API_VERSION,
    lifespan=lifespan,
)

# Robust CORS origins parsing
origins_env = os.getenv("CORS_ORIGINS", "http://localhost:3000").strip()
origins: List[str] = [o.strip() for o in origins_env.split(",") if o.strip()]

# If no valid origins, use default for development
if not origins:
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    print(f"Using default CORS origins: {origins}")

# Add CORS middleware with explicit settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

# Initialize and configure DSPy language model
try:
    LLMConfig.configure_dspy()
    print("LLM configured successfully")
except ValueError as e:
    # Allow backend to start without LLM in CI/test environments
    if "No LLM configured" in str(e):
        print(
            "Warning: No LLM configured; continuing without LLM. Set USE_OLLAMA/USE_AZURE/GROK_* to enable."
        )
    else:
        raise

# Include all routers with a common prefix
app.include_router(router)  # health check and root endpoints
app.include_router(auth_router, prefix="/api")
app.include_router(repositories_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(units_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

print(f"Backend server started successfully on port {os.getenv('BACKEND_PORT', 8000)}")
print(f"CORS enabled for origins: {origins}")
