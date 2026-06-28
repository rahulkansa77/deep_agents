"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    answer: str
    intent: str
    tools_used: list[str]
    execution_time_ms: float
    steps_taken: int = 0
    reasoning_log: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str


class AgentStatusResponse(BaseModel):
    model: str
    pdf_loaded: bool
    pdf_chunks_count: int
    excel_loaded: bool
    excel_row_count: int
    uptime_seconds: float


class UploadResponse(BaseModel):
    message: str
    details: Optional[dict] = None


class TurnSchema(BaseModel):
    user: str
    assistant: str
    intent: str
    tools: list[str]
    timestamp: str


class SessionMeta(BaseModel):
    session_id: str
    title: str
    turn_count: int
    last_updated: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    turns: list[TurnSchema]


class SessionListResponse(BaseModel):
    sessions: list[SessionMeta]
