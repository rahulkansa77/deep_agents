"""Health and agent status endpoints."""

from __future__ import annotations
import time
from fastapi import APIRouter
from app.models.schemas import HealthResponse, AgentStatusResponse
from app.knowledge.pdf_cache import pdf_cache
from app.tools.excel_sales_tool import excel_cache
from app.utils.config import get_settings

router = APIRouter()
settings = get_settings()
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "healthy"}


@router.get("/agent/status", response_model=AgentStatusResponse)
async def agent_status():
    return {
        "model": settings.model_name,
        "pdf_loaded": pdf_cache.loaded,
        "pdf_chunks_count": len(pdf_cache.chunks),
        "excel_loaded": excel_cache.loaded,
        "excel_row_count": excel_cache.row_count,
        "uptime_seconds": round(time.time() - _start_time, 2),
    }
