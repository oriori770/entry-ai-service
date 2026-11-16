import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import connect_db, disconnect_db
from app.logging_config import setup_logging
from app.routers import health, chat

logger = logging.getLogger("entry_ai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging()
    logger.info(f"[bold green]Starting {settings.app_name}[/bold green] on port {settings.port} (env: {settings.environment})")
    await connect_db()
    yield
    await disconnect_db()
    logger.info(f"[bold yellow]Shutting down {settings.app_name}[/bold yellow]")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS
    allowed_origins = settings.get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers under /api/ai
    app.include_router(health.router, prefix="/api/ai")
    app.include_router(chat.router, prefix="/api/ai")

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "message": f"{settings.app_name} is running",
            "docs": "/docs",
            "health": "/api/ai/health",
            "version": settings.app_version,
        }

    return app


app = create_app()
