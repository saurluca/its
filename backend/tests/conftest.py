import pytest
import asyncio
from typing import Generator
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import patch
import tempfile
import os
import uuid

# Import modules
from main import app
from dependencies import get_db_session
from auth.dependencies import get_current_user_from_request
from auth.models import User
from auth.service import create_access_token

# Import all models to ensure they're registered with SQLModel.metadata
from auth.models import User  # noqa
from documents.models import Document, Chunk  # noqa
from tasks.models import Task, AnswerOption  # noqa
from repositories.models import Repository  # noqa


# Test database configuration
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
TEST_DB_PATH = "./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def get_test_session() -> Generator[Session, None, None]:
    """Test database session dependency"""
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Clean up the test database file after all tests complete"""
    yield
    # Ensure engine is disposed to close all connections
    engine.dispose()

    # Clean up the test database file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.unlink(TEST_DB_PATH)
            print(f"✅ Cleaned up test database: {TEST_DB_PATH}")
        except OSError as e:
            print(f"⚠️  Warning: Could not delete test database {TEST_DB_PATH}: {e}")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test"""
    # Create tables
    SQLModel.metadata.create_all(engine)

    # Create session
    with Session(engine) as session:
        yield session

    # Clean up - drop all tables and close connections
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """Create a test client with overridden dependencies"""
    # Override the database dependency
    app.dependency_overrides[get_db_session] = lambda: db_session

    with TestClient(app) as test_client:
        yield test_client

    # Clear overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Create a mock user for testing"""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password",
        disabled=False,
    )


@pytest.fixture
def mock_current_user(mock_user):
    """Mock the current user dependency"""

    def _mock_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user_from_request] = _mock_get_current_user
    yield mock_user
    app.dependency_overrides.pop(get_current_user_from_request, None)


@pytest.fixture
def auth_headers(mock_user):
    """Create authentication headers for testing"""
    access_token = create_access_token(data={"sub": mock_user.email})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def temp_file():
    """Create a temporary file for testing file uploads"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(b"This is a test document content for testing purposes.")
        temp_file_path = f.name

    yield temp_file_path

    # Clean up
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def mock_llm_service():
    """Mock LLM service for testing"""
    with (
        patch("tasks.router.generate_questions") as mock_generate,
        patch("tasks.router.evaluate_student_answer") as mock_evaluate,
        patch("documents.router.generate_document_title") as mock_title,
    ):
        # Mock generate_questions - return empty list by default
        mock_generate.return_value = []

        # Mock evaluate_student_answer
        mock_evaluate.return_value = "Good answer! Well done."

        # Mock generate_document_title
        mock_title.return_value = "Test Document Title"

        yield {
            "generate_questions": mock_generate,
            "evaluate_student_answer": mock_evaluate,
            "generate_document_title": mock_title,
        }


# Test data fixtures
@pytest.fixture
def sample_chunk_data():
    """Sample chunk data for testing"""
    return {
        "id": uuid.uuid4(),
        "chunk_text": "This is a sample chunk text for testing purposes.",
        "chunk_index": 0,
        "document_id": uuid.uuid4(),
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for testing"""
    return {
        "type": "multiple_choice",
        "question": "What is the main topic of this text?",
        "chunk_id": uuid.uuid4(),
        "answer_options": [
            {"answer": "Option A", "is_correct": True},
            {"answer": "Option B", "is_correct": False},
            {"answer": "Option C", "is_correct": False},
        ],
    }


@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "id": uuid.uuid4(),
        "title": "Test Document",
        "source_file": "test.txt",
        "content": "This is test document content.",
    }


@pytest.fixture
def sample_repository_data():
    """Sample repository data for testing"""
    return {
        "name": "Test Repository",
        "description": "A test repository for testing purposes",
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
    }
