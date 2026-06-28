"""In-memory PDF cache — loaded once at startup, never reloaded per request."""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class PDFChunk:
    chunk_id: int
    text: str
    page_number: int
    chapter_title: str
    word_count: int


@dataclass
class PDFCache:
    pages: list[str] = field(default_factory=list)          # raw page text
    chunks: list[PDFChunk] = field(default_factory=list)    # searchable chunks
    metadata: dict = field(default_factory=dict)            # page→chapter map
    loaded: bool = False
    file_path: str = ""

    def clear(self):
        self.pages.clear()
        self.chunks.clear()
        self.metadata.clear()
        self.loaded = False
        self.file_path = ""


# Singleton cache instance shared across the application
pdf_cache = PDFCache()
