from sqlmodel import SQLModel, Session
from dependencies import get_database_engine
from typing import Generator
from sqlalchemy import text
import time


# Database utility functions
def create_db_and_tables():
    """Create database tables"""
    engine = get_database_engine()
    SQLModel.metadata.create_all(engine)


def wait_for_database(max_retries: int = 30, delay: float = 1.0):
    """Wait for database to be ready to accept connections"""

    print(f"⏳ Waiting for database to be ready (max {max_retries} attempts)...")
    engine = get_database_engine()

    for attempt in range(max_retries):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print("✅ Database is ready!")
                return True
        except Exception as e:
            print(f"⚠️  Database not ready (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)

    print("❌ Database failed to become ready")
    return False


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    engine = get_database_engine()
    with Session(engine) as session:
        yield session
