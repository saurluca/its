from pydantic import BaseModel


# General response schemas
class HealthCheckResponse(BaseModel):
    status: str
