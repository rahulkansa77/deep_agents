"""Session management endpoints — list, retrieve, and delete sessions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.agent.memory import memory_store

router = APIRouter(prefix="/sessions")


@router.get("")
async def list_sessions():
    """
    Return metadata for all active sessions.
    Used by the frontend sidebar to restore history after a page refresh.
    """
    return {"sessions": memory_store.list_sessions()}


@router.get("/{session_id}")
async def get_session(session_id: str):
    """
    Return the full turn-by-turn history for a specific session.
    Used when the user clicks a session in the sidebar.
    """
    history = memory_store.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found or empty.")
    return {
        "session_id": session_id,
        "turns": history,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """Clear a session from server memory (called on 'Clear Chat')."""
    memory_store.clear(session_id)
    return {"message": f"Session {session_id} cleared."}
