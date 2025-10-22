import os
from functools import lru_cache
import dspy
from sqlmodel import Session, create_engine
from sqlalchemy.orm import sessionmaker
from config import DatabaseConfig
from dotenv import load_dotenv

load_dotenv()


# Create engine using configuration
engine = create_engine(DatabaseConfig.get_database_url(), echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session():
    """Dependency to get database session"""
    with Session(engine) as session:
        yield session


def get_database_engine():
    """Get the database engine"""
    return engine


azure_api_key = os.getenv("AZURE_API_KEY")
azure_api_base = os.getenv("AZURE_API_BASE")


@lru_cache(maxsize=1)
def get_small_llm():
    """Get a small LLM"""
    print("getting small llm")
    if azure_api_key and azure_api_base:
        lm = dspy.LM(
            "azure/gpt-4o-mini",
            api_base=azure_api_base,
            api_key=azure_api_key,
            api_version="2024-12-01-preview",
        )
    else:
        raise ValueError("AZURE_API_KEY and AZURE_API_BASE are required.")
    return lm


@lru_cache(maxsize=1)
def get_large_llm():
    """Get a large LLM"""
    if azure_api_key and azure_api_base:
        lm = dspy.LM(
            "azure/gpt-4o-mini",
            api_base=azure_api_base,
            api_key=azure_api_key,
            api_version="2024-12-01-preview",
        )
    else:
        raise ValueError("AZURE_API_KEY and AZURE_API_BASE are required.")
    return lm


@lru_cache(maxsize=1)
def get_large_llm_no_cache():
    """Get a large LLM with no cache"""
    print("getting large llm no cache")
    if azure_api_key and azure_api_base:
        lm = dspy.LM(
            "azure/gpt-4o-mini",
            api_base=azure_api_base,
            api_key=azure_api_key,
            api_version="2024-12-01-preview",
            cache=False,
            temperature=0.4,
        )
    else:
        raise ValueError("AZURE_API_KEY and AZURE_API_BASE are required.")
    return lm
