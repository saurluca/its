from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router
from courses.router import router as courses_router
from tasks.router import router as tasks_router
from utils import create_db_and_tables
from config import LLMConfig, AppConfig

app = FastAPI(
    title="ITS Pipeline API",
    description="Intelligent Tutoring System Pipeline for document processing and question generation",
    version=AppConfig.API_VERSION,
)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
create_db_and_tables()

# Initialize and configure DSPy language model
LLMConfig.configure_dspy()

# Include all routers
app.include_router(router)
app.include_router(courses_router)
app.include_router(tasks_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
