from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.imports import router as imports_router
from app.api.routes.stations import router as stations_router

app = FastAPI(
    title="Radio Music Intelligence & Automation System",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(stations_router)
app.include_router(imports_router)
