"""Retry helper for direct LLM calls (not used by create_deep_agent itself,
which handles retries internally via tenacity).

Kept here for any utility code that needs direct LLM access outside the agent graph.
"""

from __future__ import annotations

import asyncio
import random
import logging

from app.utils.config import get_settings

logger   = logging.getLogger(__name__)
settings = get_settings()

MAX_RETRIES = 6
BASE_DELAY  = 5.0
MAX_DELAY   = 60.0
JITTER      = 2.0


def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in ("429", "quota", "rate", "503", "overloaded", "resource_exhausted"))


async def run_with_retry(coro):
    """
    Wrap any async coroutine with exponential backoff on quota / rate errors.

    Usage:
        result = await run_with_retry(some_llm.ainvoke(messages))
    """
    delay    = BASE_DELAY
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await coro
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == MAX_RETRIES:
                raise
            wait = min(delay, MAX_DELAY) + random.uniform(-JITTER, JITTER)
            wait = max(wait, 1.0)
            logger.warning(f"LLM rate error (attempt {attempt}/{MAX_RETRIES}), retrying in {wait:.1f}s — {exc}")
            await asyncio.sleep(wait)
            delay *= 2

    raise last_exc
