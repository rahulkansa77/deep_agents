"""Conversation memory — per-session rolling history, last 10 turns."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Turn:
    user: str
    assistant: str
    intent: str = ""
    tools: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ConversationMemory:
    """
    Stores up to max_turns turns per session_id.
    Provides conversation summary for the LLM and context hints for
    coreference resolution (last year, last product mentioned).
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        # session_id → list[Turn]  (capped at max_turns)
        self._sessions: dict[str, list[Turn]] = defaultdict(list)
        # session_id → first user message (used as sidebar title)
        self._titles: dict[str, str] = {}

    # ── Write ────────────────────────────────────────────────────────────────

    def add(self, session_id: str, user_msg: str, assistant_msg: str,
            intent: str = "", tools: list[str] | None = None):
        """Append a turn; evict the oldest if over the cap."""
        if session_id not in self._titles:
            self._titles[session_id] = user_msg[:60]

        turns = self._sessions[session_id]
        turns.append(Turn(
            user=user_msg,
            assistant=assistant_msg,
            intent=intent,
            tools=tools or [],
        ))
        if len(turns) > self.max_turns:
            turns.pop(0)

    def clear(self, session_id: str):
        self._sessions.pop(session_id, None)
        self._titles.pop(session_id, None)

    # ── Read ─────────────────────────────────────────────────────────────────

    def get_summary(self, session_id: str) -> str:
        """
        Return the last 5 turns formatted for the LLM system prompt.
        Uses full assistant text (no truncation) so context is not lossy.
        """
        turns = self._sessions[session_id]
        if not turns:
            return ""
        lines: list[str] = []
        for t in turns[-5:]:
            lines.append(f"User: {t.user}")
            lines.append(f"Assistant: {t.assistant}")
        return "\n".join(lines)

    def get_history(self, session_id: str) -> list[dict]:
        """Return full turn list as plain dicts (for the /sessions API)."""
        return [
            {
                "user": t.user,
                "assistant": t.assistant,
                "intent": t.intent,
                "tools": t.tools,
                "timestamp": t.timestamp,
            }
            for t in self._sessions[session_id]
        ]

    def list_sessions(self) -> list[dict]:
        """Return metadata for all active sessions (for sidebar restore)."""
        result = []
        for sid, turns in self._sessions.items():
            result.append({
                "session_id": sid,
                "title": self._titles.get(sid, "Untitled"),
                "turn_count": len(turns),
                "last_updated": turns[-1].timestamp if turns else "",
            })
        # Most recently updated first
        result.sort(key=lambda x: x["last_updated"], reverse=True)
        return result

    def extract_context_hints(self, session_id: str) -> dict:
        """
        Scan recent user messages to find the last mentioned year and product.
        Used for coreference resolution ("compare with previous year").
        """
        turns = self._sessions[session_id]
        hints: dict = {"last_year": None, "last_product": None}

        for turn in reversed(turns):
            if hints["last_year"] is None:
                m = re.search(r"\b(20\d{2})\b", turn.user)
                if m:
                    hints["last_year"] = int(m.group(1))

            if hints["last_product"] is None:
                for kw in [
                    "mechanical keyboard", "membrane keyboard",
                    "wireless keyboard", "gaming keyboard", "ergonomic keyboard",
                    "wired mouse", "wireless mouse", "gaming mouse",
                    "ergonomic mouse", "bluetooth mouse",
                ]:
                    if kw in turn.user.lower():
                        hints["last_product"] = kw
                        break

            if hints["last_year"] and hints["last_product"]:
                break

        return hints


# Application-wide singleton
memory_store = ConversationMemory(max_turns=10)
