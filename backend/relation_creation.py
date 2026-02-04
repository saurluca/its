import sys
import os

# Add the backend directory to the python path if needed (usually not needed if running from the folder)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import SQLModel, create_engine
from config import DatabaseConfig

# IMPORT ALL MODELS
# This ensures SQLModel knows about every table before creating them.
from auth.models import User
from repositories.models import Repository
from tasks.models import Task, AnswerOption
from documents.models import Document, Chunk
from skills.models import Skill, UserSkillLink, RepositorySkillLink
from analytics.models import PageType, UserPageSession
from reports.models import Report
from units.models import Unit, UnitTaskLink  # Explicitly importing Unit to solve the circular dependency

def init_db():
    """Create all tables in the database."""
    print("Connecting to database...")
    engine = create_engine(DatabaseConfig.get_database_url(), echo=True)
    
    print("Creating tables...")
    # This will create all tables that are registered in SQLModel.metadata
    SQLModel.metadata.create_all(engine)
    
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()