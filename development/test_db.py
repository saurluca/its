from pathlib import Path
from sqlalchemy import text
from sqlmodel import create_engine
from dotenv import load_dotenv
import os

# Ensure we load environment variables from the project root .env
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


def get_database_url():
    return f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"


def main() -> int:
    print("Testing database connection...")
    db_url = get_database_url()
    print("Database URL:", db_url)
    # Set connect_args with a 4 second timeout
    engine = create_engine(db_url, echo=False, connect_args={"connect_timeout": 3})
    print("Engine created")
    print("Connecting to database...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
            print(f"Database connection OK. SELECT 1 -> {result}")
        return 0
    except Exception as exc:  # pragma: no cover
        print(f"Database connection FAILED: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
