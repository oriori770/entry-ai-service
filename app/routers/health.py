from fastapi import APIRouter, Depends
from app.config import Settings, get_settings
from app.database import is_db_connected

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Health Check")
async def health_check(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "connected" if is_db_connected() else "disconnected",
    }
