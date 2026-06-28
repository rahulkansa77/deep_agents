"""Utility helpers."""

import re


def clean_text(text: str) -> str:
    """Normalize whitespace in extracted text."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i: i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


def truncate(text: str, max_chars: int = 4000) -> str:
    return text[:max_chars] + "..." if len(text) > max_chars else text
