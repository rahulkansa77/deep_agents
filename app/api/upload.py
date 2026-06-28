"""Upload endpoints for PDF and Excel replacement."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import UploadResponse
from app.startup import load_pdf, load_excel
from app.utils.config import get_settings

router = APIRouter(prefix="/upload")
settings = get_settings()


@router.post("/pdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Replace the current PDF and reload cache without restarting."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files accepted.")

    dest = Path(settings.pdf_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    success = load_pdf(str(dest))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process uploaded PDF.")

    from app.knowledge.pdf_cache import pdf_cache
    return UploadResponse(
        message="PDF uploaded and cache refreshed.",
        details={"chunks": len(pdf_cache.chunks), "pages": len(pdf_cache.pages)},
    )


@router.post("/excel", response_model=UploadResponse)
async def upload_excel(file: UploadFile = File(...)):
    """Replace the current Excel file and reload cache without restarting."""
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx/.xls files accepted.")

    dest = Path(settings.excel_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    success = load_excel(str(dest))
    if not success:
        raise HTTPException(status_code=500, detail="Failed to process uploaded Excel.")

    from app.tools.excel_sales_tool import excel_cache
    return UploadResponse(
        message="Excel uploaded and cache refreshed.",
        details={"rows": excel_cache.row_count},
    )
