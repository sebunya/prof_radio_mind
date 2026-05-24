from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_SERVICE = "radio-music-intelligence"
_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service=_SERVICE, version=_VERSION)
