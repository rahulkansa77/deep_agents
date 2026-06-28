"""Chat endpoint — runs the Deep Agent via create_deep_agent."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.agent.graph import build_agent, format_user_message
from app.agent.memory import memory_store
from app.models.schemas import ChatRequest, ChatResponse
from app.utils.logger import get_logger, log_request

router = APIRouter()
logger = get_logger(__name__)


def _extract_tool_usage(messages: list) -> tuple[list[str], list[str]]:
    """
    Walk the message thread and extract:
    - tools_used    : unique tool names actually called
    - reasoning_log : step-by-step trace of tool calls and observations
    """
    tools_used: list[str]    = []
    reasoning_log: list[str] = []
    step = 0

    for msg in messages:
        if isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    step += 1
                    name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                    args = tc.get("args", {})        if isinstance(tc, dict) else getattr(tc, "args", {})
                    if name not in tools_used:
                        tools_used.append(name)
                    reasoning_log.append(f"Step {step} | TOOL CALL: {name} | ARGS: {args}")
            elif msg.content:
                reasoning_log.append(f"THOUGHT: {str(msg.content)[:300]}")

        elif isinstance(msg, ToolMessage):
            tool_name = getattr(msg, "name", "tool")
            reasoning_log.append(f"OBSERVATION ({tool_name}): {str(msg.content)[:400]}")

    return tools_used, reasoning_log


def _intent_from_tools(tools_used: list[str]) -> str:
    has_pdf   = any("report" in t for t in tools_used)
    has_excel = any("sales"  in t for t in tools_used)
    if has_pdf and has_excel:
        return "BOTH"
    if has_pdf:
        return "REPORT"
    if has_excel:
        return "SALES"
    return "GENERAL"


def _get_messages(result: dict) -> list:
    """Returns the message list from the agent result."""
    return result.get("messages", [])


def _extract_text(content) -> str:
    """Normalise AIMessage.content — handles both plain strings and
    list-of-block formats returned by create_deep_agent."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(p for p in parts if p).strip()
    return str(content).strip()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user message through the Deep Agent."""
    start      = time.time()
    session_id = request.session_id or "default"

    hints   = memory_store.extract_context_hints(session_id)
    summary = memory_store.get_summary(session_id)

    # Coreference resolution — "previous year" → inject the actual year
    enriched_msg = request.message
    if hints.get("last_year") and any(
        kw in request.message.lower()
        for kw in ["previous year", "last year", "prior year", "year before"]
    ):
        enriched_msg = request.message + f" (referring to {hints['last_year'] - 1})"

    try:
        agent  = build_agent()
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=format_user_message(enriched_msg, summary))]}
        )
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

    all_messages = _get_messages(result)

    # Final answer = last AIMessage that has content and no pending tool calls
    final_answer = ""
    for msg in reversed(all_messages):
        if isinstance(msg, AIMessage):
            tool_calls = getattr(msg, "tool_calls", None) or []
            if msg.content and not tool_calls:
                final_answer = _extract_text(msg.content)
                break

    if not final_answer:
        final_answer = "I was unable to generate a response."

    tools_used, reasoning_log = _extract_tool_usage(all_messages)
    intent    = _intent_from_tools(tools_used)
    exec_time = time.time() - start

    memory_store.add(
        session_id,
        request.message,
        final_answer,
        intent=intent,
        tools=tools_used,
    )

    pdf_chunks = sum(1 for t in tools_used if "report" in t)
    log_request(logger, request.message, intent, tools_used, exec_time, pdf_chunks)

    return ChatResponse(
        answer=final_answer,
        intent=intent,
        tools_used=tools_used,
        execution_time_ms=round(exec_time * 1000, 2),
        steps_taken=len([m for m in all_messages if isinstance(m, ToolMessage)]),
        reasoning_log=reasoning_log,
    )
