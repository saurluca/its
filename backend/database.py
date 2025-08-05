from sqlmodel import SQLModel, Session
from dependencies import get_database_engine
from typing import Generator


# Database utility functions
def create_db_and_tables():
    """Create database tables"""
    engine = get_database_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    engine = get_database_engine()
    with Session(engine) as session:
        yield session
