"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

# Inject GOOGLE_API_KEY into os.environ BEFORE any agent/LLM imports.
from app.utils.config import get_settings as _get_settings
_get_settings().inject_env()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, upload, sessions
from app.startup import startup
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — loading PDF and Excel caches...")
    startup()
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Rahul Technologies Deep Agent",
    version="1.0.0",
    description="Production-ready LangGraph + FastAPI agent for Rahul Technologies.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(sessions.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
