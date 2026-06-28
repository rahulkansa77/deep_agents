"""Tool functions for the Deep Agent.

Plain Python functions with docstrings — exactly the pattern from the
deepagents documentation. create_deep_agent wraps them automatically.
No @tool decorator needed.
"""

from __future__ import annotations

from app.tools.pdf_reader import search_pdf, format_pdf_context
from app.tools.excel_sales_tool import analyse_sales
from app.utils.logger import get_logger

logger = get_logger(__name__)


def search_company_report(query: str) -> str:
    """Search the Rahul Technologies corporate PDF report for relevant information.

    Use for: company strategy, vision, future plans, roadmap, financial performance,
    revenue targets, market analysis, partnerships, expansions, product launches,
    and any detailed narrative content from the annual or corporate report.

    Args:
        query: The specific topic or question to search for in the PDF report.

    Returns:
        Relevant text excerpts from the report with page numbers and section titles.
    """
    results = search_pdf(query, top_k=5)
    context = format_pdf_context(results)
    logger.info(f"PDF tool called: query='{query[:60]}' | chunks={len(results)}")
    return context


def analyse_company_sales(query: str) -> str:
    """Analyse the Rahul Technologies sales Excel data from 2020 to 2025.

    Use for: units sold or produced for any product, month, quarter, or year,
    sales trends, growth rates, YOY comparisons, MOM comparisons, CAGR calculations,
    best selling and worst selling products, keyboard vs mouse category comparisons,
    monthly or quarterly breakdowns, moving averages, and trend analysis.

    Products: Mechanical Keyboard, Membrane Keyboard, Wireless Keyboard,
    Gaming Keyboard, Ergonomic Keyboard, Wired Mouse, Wireless Mouse,
    Gaming Mouse, Ergonomic Mouse, Bluetooth Mouse.

    Years available: 2020, 2021, 2022, 2023, 2024, 2025.

    Args:
        query: The specific sales question including product name, time period, and metric.

    Returns:
        Markdown-formatted sales analysis with totals, breakdowns, and trends.
    """
    result = analyse_sales(query)
    logger.info(f"Excel tool called: query='{query[:60]}'")
    return result
