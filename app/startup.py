"""Application startup — loads PDF and Excel into memory caches."""

from __future__ import annotations

import re
from pathlib import Path

from app.utils.config import get_settings
from app.utils.helpers import clean_text, chunk_text
from app.utils.logger import get_logger
from app.knowledge.pdf_cache import pdf_cache, PDFChunk
from app.tools.excel_sales_tool import excel_cache, _normalise_columns

logger = get_logger(__name__)
settings = get_settings()


# ── Helpers ─────────────────────────────────────────────────────────────────

def _detect_chapter(text: str, fallback: str) -> str:
    """Detect chapter/section title from the first non-empty line."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and len(stripped) < 80:
            return stripped
    return fallback


# ── PDF Loader ───────────────────────────────────────────────────────────────

def load_pdf(path: str | None = None) -> bool:
    """Load PDF into pdf_cache. Returns True on success."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed.")
        return False

    pdf_path = Path(path or settings.pdf_path)
    if not pdf_path.exists():
        logger.error(f"PDF not found at {pdf_path}")
        return False

    pdf_cache.clear()
    doc = fitz.open(str(pdf_path))
    full_text_parts: list[str] = []
    current_chapter = "Introduction"

    for page_num, page in enumerate(doc, start=1):
        raw = page.get_text()
        cleaned = clean_text(raw)
        pdf_cache.pages.append(cleaned)

        # Try to detect chapter from first significant line
        chapter = _detect_chapter(cleaned, current_chapter)
        if chapter != current_chapter:
            current_chapter = chapter
            pdf_cache.metadata[page_num] = chapter

        full_text_parts.append(cleaned)

    doc.close()

    # Build chunks from full text with page tracking
    chunk_id = 0
    for page_num, page_text in enumerate(pdf_cache.pages, start=1):
        chapter = pdf_cache.metadata.get(page_num, "General")
        for chunk_text_item in chunk_text(page_text, chunk_size=800, overlap=150):
            if len(chunk_text_item.strip()) < 50:
                continue
            pdf_cache.chunks.append(
                PDFChunk(
                    chunk_id=chunk_id,
                    text=chunk_text_item,
                    page_number=page_num,
                    chapter_title=chapter,
                    word_count=len(chunk_text_item.split()),
                )
            )
            chunk_id += 1

    pdf_cache.loaded = True
    pdf_cache.file_path = str(pdf_path)
    logger.info(f"PDF loaded: {pdf_path.name} | pages={len(pdf_cache.pages)} | chunks={len(pdf_cache.chunks)}")
    return True


# ── Excel Loader ─────────────────────────────────────────────────────────────

def load_excel(path: str | None = None) -> bool:
    """Load Excel into excel_cache. Returns True on success."""
    try:
        import pandas as pd
    except ImportError:
        logger.error("Pandas not installed.")
        return False

    excel_path = Path(path or settings.excel_path)
    if not excel_path.exists():
        logger.error(f"Excel not found at {excel_path}")
        return False

    excel_cache.clear()
    try:
        df = pd.read_excel(str(excel_path), engine="openpyxl")
        df = _normalise_columns(df)
        excel_cache.df = df
        excel_cache.loaded = True
        excel_cache.file_path = str(excel_path)
        excel_cache.row_count = len(df)
        logger.info(f"Excel loaded: {excel_path.name} | rows={len(df)} | cols={list(df.columns)}")
        return True
    except Exception as e:
        logger.error(f"Excel load error: {e}")
        return False


# ── Entry point ───────────────────────────────────────────────────────────────

def startup():
    """Run at application startup to pre-load all data files."""
    load_pdf()
    load_excel()
