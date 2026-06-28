"""Excel sales analysis tool — operates on a cached Pandas DataFrame.

Real schema: Year, Month (Jan-Dec abbrev), Category, Product, Produced, Sold
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

MONTH_ORDER = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
MONTH_NUM   = {m: i+1 for i, m in enumerate(MONTH_ORDER)}
QUARTER_MAP = {1:[1,2,3], 2:[4,5,6], 3:[7,8,9], 4:[10,11,12]}


@dataclass
class ExcelCache:
    df: Optional[pd.DataFrame] = None
    loaded: bool = False
    file_path: str = ""
    row_count: int = 0

    def clear(self):
        self.df = None
        self.loaded = False
        self.file_path = ""
        self.row_count = 0


# Singleton
excel_cache = ExcelCache()


def _normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise column names to lowercase and add month_num helper."""
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        "Year":     "year",
        "Month":    "month",
        "Category": "category",
        "Product":  "product",
        "Produced": "units_produced",
        "Sold":     "units_sold",
    })
    df["year"]          = pd.to_numeric(df["year"],          errors="coerce").astype("Int64")
    df["units_produced"] = pd.to_numeric(df["units_produced"], errors="coerce").fillna(0).astype(int)
    df["units_sold"]     = pd.to_numeric(df["units_sold"],     errors="coerce").fillna(0).astype(int)
    df["month_num"]      = df["month"].map(MONTH_NUM)
    return df


# ── Query parsing helpers ────────────────────────────────────────────────────

def _parse_year(q: str) -> Optional[int]:
    m = re.search(r"\b(20\d{2})\b", q)
    return int(m.group(1)) if m else None


def _parse_month(q: str) -> Optional[str]:
    long_to_abbr = {
        "january":"Jan","february":"Feb","march":"Mar","april":"Apr",
        "may":"May","june":"Jun","july":"Jul","august":"Aug",
        "september":"Sep","october":"Oct","november":"Nov","december":"Dec",
    }
    abbr = {v.lower(): v for v in MONTH_ORDER}
    for full, abbr_val in long_to_abbr.items():
        if full in q:
            return abbr_val
    for short, abbr_val in abbr.items():
        # match word-boundary e.g. "jan" not inside "january"
        if re.search(rf"\b{short}\b", q):
            return abbr_val
    return None


def _parse_quarter(q: str) -> Optional[int]:
    m = re.search(r"\bq([1-4])\b", q)
    return int(m.group(1)) if m else None


def _parse_product(q: str) -> Optional[str]:
    for p in ["mechanical keyboard","membrane keyboard","wireless keyboard",
              "gaming keyboard","ergonomic keyboard",
              "wired mouse","wireless mouse","gaming mouse",
              "ergonomic mouse","bluetooth mouse"]:
        if p in q:
            return p
    return None


def _parse_category(q: str) -> Optional[str]:
    has_kb = "keyboard" in q
    has_ms = "mouse" in q or "mice" in q
    if has_kb and not has_ms:
        return "keyboard"
    if has_ms and not has_kb:
        return "mouse"
    return None


def _filter(df: pd.DataFrame, year, month, quarter, product, category) -> pd.DataFrame:
    if year:
        df = df[df["year"] == year]
    if month:
        df = df[df["month"] == month]
    if quarter:
        nums = QUARTER_MAP[quarter]
        df = df[df["month_num"].isin(nums)]
    if product:
        df = df[df["product"].str.lower() == product]
    if category:
        df = df[df["category"].str.lower() == category]
    return df


# ── Main analysis function ───────────────────────────────────────────────────

def analyse_sales(query: str) -> str:
    """Analyse cached DataFrame and return a markdown-formatted answer."""
    if not excel_cache.loaded or excel_cache.df is None:
        return "Excel data not loaded. Please upload the sales Excel file first."

    df  = excel_cache.df.copy()
    q   = query.lower()

    year     = _parse_year(q)
    month    = _parse_month(q)
    quarter  = _parse_quarter(q)
    product  = _parse_product(q)
    category = _parse_category(q)

    filtered = _filter(df, year, month, quarter, product, category)

    if filtered.empty:
        avail_years = sorted(df["year"].dropna().unique().tolist())
        return (f"No data found for the given filters "
                f"(year={year}, month={month}, quarter={quarter}, "
                f"product={product}, category={category}). "
                f"Available years: {avail_years}")

    lines: list[str] = []

    # ── Context header ──────────────────────────────────────────────────────
    ctx_parts = []
    if year:     ctx_parts.append(str(year))
    if quarter:  ctx_parts.append(f"Q{quarter}")
    if month:    ctx_parts.append(month)
    if product:  ctx_parts.append(product.title())
    if category: ctx_parts.append(category.title())
    ctx = " | ".join(ctx_parts) if ctx_parts else "All Data"
    lines.append(f"### Sales Analysis — {ctx}\n")

    total_sold     = int(filtered["units_sold"].sum())
    total_produced = int(filtered["units_produced"].sum())
    lines.append(f"- **Total Units Sold:** {total_sold:,}")
    lines.append(f"- **Total Units Produced:** {total_produced:,}")
    if total_produced > 0:
        sell_through = total_sold / total_produced * 100
        lines.append(f"- **Sell-through Rate:** {sell_through:.1f}%")

    # ── Product breakdown ───────────────────────────────────────────────────
    if not product and "product" not in q.replace("product",""):
        prod_grp = (filtered.groupby("product")["units_sold"]
                    .sum().sort_values(ascending=False))
        if len(prod_grp) > 1:
            lines.append("\n**Units Sold by Product:**")
            for p, v in prod_grp.items():
                lines.append(f"  - {p}: {v:,}")
            lines.append(f"\n**Best Seller:** {prod_grp.index[0]} ({prod_grp.iloc[0]:,} units)")
            lines.append(f"**Worst Seller:** {prod_grp.index[-1]} ({prod_grp.iloc[-1]:,} units)")

    # ── Category breakdown ──────────────────────────────────────────────────
    if not category and ("keyboard" in q or "mouse" in q or "categor" in q or "compare" in q or "vs" in q):
        cat_grp = (filtered.groupby("category")["units_sold"]
                   .sum().sort_values(ascending=False))
        lines.append("\n**Units Sold by Category:**")
        for c, v in cat_grp.items():
            lines.append(f"  - {c}: {v:,}")

    # ── Monthly breakdown (when no specific month requested) ────────────────
    if not month and not quarter and year:
        m_grp = (filtered.groupby("month_num")["units_sold"].sum())
        if len(m_grp) > 1:
            lines.append(f"\n**Monthly Units Sold ({year}):**")
            for mn, v in m_grp.sort_index().items():
                abbr = MONTH_ORDER[mn - 1]
                lines.append(f"  - {abbr}: {v:,}")

    # ── Quarterly breakdown ─────────────────────────────────────────────────
    if not quarter and year and "quarter" in q:
        lines.append(f"\n**Quarterly Units Sold ({year}):**")
        for qn, months_nums in QUARTER_MAP.items():
            q_data = filtered[filtered["month_num"].isin(months_nums)]
            lines.append(f"  - Q{qn}: {int(q_data['units_sold'].sum()):,}")

    # ── YOY ─────────────────────────────────────────────────────────────────
    if "yoy" in q or "year over year" in q or "yearly" in q or "annual" in q:
        scope = _filter(df, None, month, quarter, product, category)
        yoy   = scope.groupby("year")["units_sold"].sum().sort_index()
        lines.append("\n**Year-over-Year Units Sold:**")
        prev = None
        for yr, val in yoy.items():
            if prev is not None and prev > 0:
                pct = (val - prev) / prev * 100
                lines.append(f"  - {yr}: {int(val):,}  ({pct:+.1f}% YOY)")
            else:
                lines.append(f"  - {yr}: {int(val):,}")
            prev = val

    # ── MOM ─────────────────────────────────────────────────────────────────
    if "mom" in q or "month over month" in q:
        scope = _filter(df, year, None, None, product, category)
        mom   = scope.groupby("month_num")["units_sold"].sum().sort_index()
        lines.append(f"\n**Month-over-Month Units Sold{' (' + str(year) + ')' if year else ''}:**")
        prev = None
        for mn, val in mom.items():
            abbr = MONTH_ORDER[mn - 1]
            if prev is not None and prev > 0:
                pct = (val - prev) / prev * 100
                lines.append(f"  - {abbr}: {int(val):,}  ({pct:+.1f}% MOM)")
            else:
                lines.append(f"  - {abbr}: {int(val):,}")
            prev = val

    # ── CAGR ────────────────────────────────────────────────────────────────
    if "cagr" in q:
        scope = _filter(df, None, month, quarter, product, category)
        yoy   = scope.groupby("year")["units_sold"].sum().sort_index()
        if len(yoy) >= 2:
            v0, vn, n = yoy.iloc[0], yoy.iloc[-1], len(yoy) - 1
            cagr = ((vn / v0) ** (1 / n) - 1) * 100 if v0 > 0 else 0
            lines.append(f"\n**CAGR ({int(yoy.index[0])}–{int(yoy.index[-1])}):** {cagr:.2f}% per year")

    # ── Moving average ───────────────────────────────────────────────────────
    if "moving average" in q or " ma " in q:
        scope = _filter(df, year, None, None, product, category)
        monthly = scope.groupby("month_num")["units_sold"].sum().sort_index()
        ma3 = monthly.rolling(3).mean().dropna()
        if not ma3.empty:
            lines.append("\n**3-Month Moving Average (Units Sold):**")
            for mn, val in ma3.items():
                lines.append(f"  - {MONTH_ORDER[int(mn)-1]}: {val:,.0f}")

    # ── Summary across all years (no filters) ────────────────────────────────
    if not any([year, month, quarter, product, category]):
        yoy_all = df.groupby("year")["units_sold"].sum().sort_index()
        lines.append("\n**All-Years Summary:**")
        for yr, val in yoy_all.items():
            lines.append(f"  - {int(yr)}: {int(val):,} units sold")

    return "\n".join(lines)
