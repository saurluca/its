from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router
from tasks.router import router as tasks_router
from documents.router import router as documents_router
from repositories.router import router as repositories_router
from auth.router import router as auth_router
from skills.router import router as skills_router
from config import LLMConfig, AppConfig
from dotenv import load_dotenv
import os
from typing import List
from database import wait_for_database

# Import all models to register them with SQLModel.metadata
from auth.models import User  # noqa
from documents.models import Document, Chunk  # noqa
from tasks.models import Task, AnswerOption  # noqa
from repositories.models import Repository  # noqa
from skills.models import Skill, UserSkillLink, RepositorySkillLink  # noqa

load_dotenv()

# Wait for database to be ready only in CI test deployment
if os.getenv("TEST_DEPLOYMENT", "false").lower() == "true":
    print("🚀 TEST_DEPLOYMENT detected: waiting for database readiness...")
    if not wait_for_database():
        print("❌ Failed to connect to database. Exiting.")
        exit(1)

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

# Create database tables on startup only in CI test deployment
if os.getenv("TEST_DEPLOYMENT", "false").lower() == "true":
    from database import create_db_and_tables

    print("Creating database tables (TEST_DEPLOYMENT)...")
    try:
        create_db_and_tables()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️  Database table creation failed: {e}")
        print("Continuing without table creation - tables might already exist")

# Initialize and configure DSPy language model
try:
    LLMConfig.configure_dspy()
except ValueError as e:
    # Allow backend to start without LLM in CI/test environments
    if "No LLM configured" in str(e):
        print(
            "Warning: No LLM configured; continuing without LLM. Set USE_OLLAMA/USE_AZURE/GROK_* to enable."
        )
    else:
        raise

# Include all routers
app.include_router(router)  # health check and root endpoints
app.include_router(auth_router)
app.include_router(repositories_router)
app.include_router(tasks_router)
app.include_router(documents_router)
app.include_router(skills_router)

# hello world

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
