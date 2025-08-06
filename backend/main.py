from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router
from tasks.router import router as tasks_router
from documents.router import router as documents_router
from repositories.router import router as repositories_router
from auth.router import router as auth_router
from database import create_db_and_tables
from config import LLMConfig, AppConfig
from auth.dependencies import get_current_user_from_request

app = FastAPI(
    title="ITS Backend",
    description="Backend for Intelligent Tutoring System",
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
app.include_router(auth_router)
app.include_router(
    repositories_router,
    # dependencies=[Depends(get_current_user_from_request)]
)
app.include_router(
    tasks_router,
    # dependencies=[Depends(get_current_user_from_request)],
)
app.include_router(
    documents_router,
    # dependencies=[Depends(get_current_user_from_request)],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
