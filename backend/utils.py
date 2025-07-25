from sqlmodel import SQLModel, Session
from dependencies import get_database_engine


# Database utility functions
def create_db_and_tables():
    """Create database tables"""
    engine = get_database_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session"""
    engine = get_database_engine()
    return Session(engine)
