"""Deep Agent graph — built with create_deep_agent from deepagents package.

Follows exactly the documented pattern:
    pip install -U deepagents langchain-google-genai

    from deepagents import create_deep_agent
    agent = create_deep_agent(
        model="google_genai:gemini-flash-latest",
        tools=[...],
        system_prompt="...",
    )
    agent.invoke({"messages": [{"role": "user", "content": "..."}]})
"""

from __future__ import annotations

from deepagents import create_deep_agent

from app.agent.tools import search_company_report, analyse_company_sales  # noqa: F401 (re-exported)
from app.knowledge.company_knowledge import COMPANY_KNOWLEDGE
from app.utils.config import get_settings

settings = get_settings()

_BASE_SYSTEM_PROMPT = f"""You are an intelligent assistant for Rahul Technologies — a premium Indian computer peripheral company.

You have access to two tools:
1. search_company_report  — searches the corporate PDF report (strategy, future plans, financials, market analysis)
2. analyse_company_sales  — analyses the Excel sales data 2020-2025 (units sold/produced, trends, CAGR, YOY, MOM)

Built-in Company Knowledge (answer directly WITHOUT calling any tool if the answer is covered here):
{COMPANY_KNOWLEDGE}

Rules:
- Think before acting. Only call a tool when built-in knowledge is clearly insufficient.
- After a tool returns results, decide if you have enough to answer. Do not call tools redundantly.
- Never call the same tool twice with the same query.
- Present numbers and data in structured markdown: tables, bullet points, bold headings.
- Be concise, accurate, and professional.
- If information is genuinely unavailable in any source, say so honestly."""

# Singleton agent — built once at first use, reused across all requests.
_agent = None


def reset_agent():
    """Force rebuild on next request — call after .env changes."""
    global _agent
    _agent = None


def get_agent():
    """Return the shared Deep Agent instance, building it once on first call."""
    global _agent
    if _agent is None:
        import os
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.google_api_key or os.environ.get("GOOGLE_API_KEY", "")
        model   = settings.model_name.replace("google_genai:", "")

        llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=settings.temperature,
            google_api_key=api_key,
        )
        _agent = create_deep_agent(
            model=llm,
            tools=[search_company_report, analyse_company_sales],
            system_prompt=_BASE_SYSTEM_PROMPT,
        )
    return _agent


def build_agent(conversation_summary: str = ""):
    """Return the shared agent. Summary is injected into the message thread instead."""
    return get_agent()


def format_user_message(user_msg: str, conversation_summary: str) -> str:
    """Prepend session memory to the user message so the agent has context."""
    if not conversation_summary:
        return user_msg
    return f"Conversation history so far:\n{conversation_summary}\n\nUser: {user_msg}"
