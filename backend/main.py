from fastapi import FastAPI
from router import router
from utils import create_db_and_tables
from config import LLMConfig, AppConfig

app = FastAPI(
    title="ITS Pipeline API",
    description="Intelligent Tutoring System Pipeline for document processing and question generation",
    version=AppConfig.API_VERSION,
)

# Initialize database tables
create_db_and_tables()

# Initialize and configure DSPy language model
LLMConfig.configure_dspy()

# Include the main router
app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
