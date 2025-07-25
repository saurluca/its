from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from schemas import HealthCheckResponse
from constants import ROOT_MESSAGE, HEALTH_CHECK_MESSAGE

router = APIRouter()


@router.get("/", response_class=PlainTextResponse)
def read_root():
    """
    Root endpoint for the API.
    Returns a simple greeting message to verify the API is running.
    """
    return ROOT_MESSAGE


@router.get("/health", response_model=HealthCheckResponse)
def health_check():
    """
    Health check endpoint.
    Returns a JSON object indicating the service status.
    Useful for monitoring and deployment checks.
    """
    return HEALTH_CHECK_MESSAGE
