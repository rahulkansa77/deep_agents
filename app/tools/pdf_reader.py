"""PDF reader tool — searches in-memory chunks, never rereads the file."""

import re
from app.knowledge.pdf_cache import pdf_cache, PDFChunk
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _score_chunk(chunk: PDFChunk, keywords: list[str]) -> float:
    """Simple keyword frequency score (case-insensitive)."""
    text_lower = chunk.text.lower()
    return sum(text_lower.count(kw.lower()) for kw in keywords)


def extract_keywords(query: str) -> list[str]:
    """Extract meaningful tokens from query (strips stopwords)."""
    stopwords = {
        "what", "how", "when", "where", "which", "who", "why",
        "is", "are", "was", "were", "the", "a", "an", "of",
        "in", "on", "at", "to", "for", "and", "or", "with",
        "about", "tell", "me", "please", "can", "you", "do",
        "does", "did", "has", "have", "had",
    }
    tokens = re.findall(r"[a-zA-Z0-9]+", query.lower())
    return [t for t in tokens if t not in stopwords and len(t) > 2]


def search_pdf(query: str, top_k: int = 5) -> list[dict]:
    """
    Search cached PDF chunks using keyword scoring.

    Returns a list of the top-k relevant chunk dicts:
        {chunk_id, page_number, chapter_title, text, score}
    """
    if not pdf_cache.loaded or not pdf_cache.chunks:
        return [{"error": "PDF not loaded. Please upload a PDF file first."}]

    keywords = extract_keywords(query)
    if not keywords:
        keywords = query.lower().split()

    scored = [
        (chunk, _score_chunk(chunk, keywords))
        for chunk in pdf_cache.chunks
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]

    results = []
    for chunk, score in top:
        if score == 0:
            continue
        results.append({
            "chunk_id": chunk.chunk_id,
            "page_number": chunk.page_number,
            "chapter_title": chunk.chapter_title,
            "text": chunk.text,
            "score": score,
        })

    if not results and pdf_cache.chunks:
        # Return first few chunks as fallback
        results = [
            {
                "chunk_id": c.chunk_id,
                "page_number": c.page_number,
                "chapter_title": c.chapter_title,
                "text": c.text,
                "score": 0,
            }
            for c in pdf_cache.chunks[:3]
        ]

    logger.info(f"PDF search: query='{query}', keywords={keywords}, results={len(results)}")
    return results


def format_pdf_context(results: list[dict]) -> str:
    """Format search results into a readable context block for the LLM."""
    if not results or "error" in results[0]:
        return results[0].get("error", "No PDF context available.") if results else "No PDF context."

    parts = []
    for r in results:
        parts.append(
            f"[Page {r['page_number']} | {r['chapter_title']}]\n{r['text']}"
        )
    return "\n\n---\n\n".join(parts)
