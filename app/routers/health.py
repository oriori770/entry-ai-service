from fastapi import APIRouter, Depends
from app.config import Settings, get_settings

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="Health Check")
async def health_check(settings: Settings = Depends(get_settings)):
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }
