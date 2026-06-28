# Rahul Technologies — Deep Agent

A production-ready Deep Agent built with **FastAPI** and the **`deepagents`** package using `create_deep_agent`. The agent answers questions about Rahul Technologies by autonomously reasoning, deciding which tools to call, observing results, and looping until it has a complete answer.

---

## Table of Contents

1. [What Makes This a Real Deep Agent](#what-makes-this-a-real-deep-agent)
2. [Architecture Overview](#architecture-overview)
3. [Full Agent Flow](#full-agent-flow)
4. [Deep Agent Loop — How It Works](#deep-agent-loop--how-it-works)
5. [Tools](#tools)
6. [Conversation Memory](#conversation-memory)
7. [Retry & Rate Limit Handling](#retry--rate-limit-handling)
8. [Data Caching Strategy](#data-caching-strategy)
9. [Folder Structure](#folder-structure)
10. [Installation](#installation)
11. [Environment Variables](#environment-variables)
12. [Running the Server](#running-the-server)
13. [Running the Frontend](#running-the-frontend)
14. [API Reference](#api-reference)
15. [Session Management](#session-management)
16. [Logs](#logs)
---

## What Makes This a Real Deep Agent

This project uses the **official `deepagents` package** with `create_deep_agent`.

| Aspect | Description |
|--------|-------------|
| Tool decision | LLM reasons autonomously about which tool to call |
| Loop | Loops until confident — calls tools multiple times if needed |
| Tool calling | Plain Python functions with docstrings — `create_deep_agent` wraps them automatically |
| Observations | LLM reads tool return values and decides what to do next |
| Stopping | LLM decides to stop when it has enough information to answer |
| State | Message thread managed internally by `create_deep_agent` |

The agent is the LLM itself. It decides what to think, what to call, when to loop, and when to stop.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Rahul Technologies Deep Agent                 │
│                                                                  │
│  ┌──────────┐    ┌─────────────────────────────────────────┐    │
│  │ FastAPI  │    │      create_deep_agent (deepagents)      │    │
│  │          │    │                                          │    │
│  │  /chat   │───►│  system_prompt                           │    │
│  │          │    │  (company knowledge + session memory)    │    │
│  │  /health │    │              │                           │    │
│  │          │    │              ▼                           │    │
│  │ /sessions│    │         ┌─────────┐                      │    │
│  │          │    │         │   LLM   │                      │    │
│  │ /upload  │    │         │ Gemini  │                      │    │
│  └──────────┘    │         └────┬────┘                      │    │
│                  │              │                           │    │
│                  │    ┌─────────▼──────────┐                │    │
│                  │    │  tool_calls in msg?│                │    │
│                  │    └──┬──────────────┬──┘                │    │
│                  │    yes│              │no                 │    │
│                  │       ▼              ▼                   │    │
│                  │  ┌─────────┐    ┌────────┐               │    │
│                  │  │  Tools  │    │  END   │               │    │
│                  │  │  Node   │    └────────┘               │    │
│                  │  │         │                             │    │
│                  │  │ search_ │                             │    │
│                  │  │ company_│                             │    │
│                  │  │ report  │                             │    │
│                  │  │         │                             │    │
│                  │  │ analyse_│                             │    │
│                  │  │ company_│                             │    │
│                  │  │ sales   │                             │    │
│                  │  └────┬────┘                             │    │
│                  │       │ ToolMessage                      │    │
│                  │       └──────────► LLM (loop back)       │    │
│                  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

## Full Agent Flow

```
  POST /chat  { "message": "...", "session_id": "uuid" }
       │
       ▼
  chat.py
  ├─ memory_store.extract_context_hints()  → last_year, last_product
  ├─ memory_store.get_summary()            → last 5 turns as text
  ├─ coreference resolution               → enrich query if needed
  └─ build_agent(conversation_summary)    → creates fresh agent with system prompt
       │
       ▼
  create_deep_agent.ainvoke({"messages": [HumanMessage]})
       │
       ▼
  ┌──────────────────────────────────────────────────────┐
  │                  Deep Agent Loop                      │
  │                                                       │
  │  [HumanMessage: user question]                        │
  │          │                                            │
  │          ▼                                            │
  │     LLM thinks:                                       │
  │     "I need to check the sales data for 2024"         │
  │          │                                            │
  │          ▼  AIMessage with tool_calls                 │
  │  ┌───────────────────────────┐                        │
  │  │ tool: analyse_company_    │                        │
  │  │ sales("2024 keyboard      │                        │
  │  │  units sold")             │                        │
  │  └───────────┬───────────────┘                        │
  │              │                                        │
  │              ▼  ToolMessage                           │
  │  "### Sales Analysis — 2024 | Keyboard               │
  │   Total Units Sold: 12,450 ..."                       │
  │              │                                        │
  │              ▼                                        │
  │     LLM thinks:                                       │
  │     "Now I also need the strategy context"            │
  │          │                                            │
  │          ▼  AIMessage with tool_calls                 │
  │  ┌───────────────────────────┐                        │
  │  │ tool: search_company_     │                        │
  │  │ report("keyboard 2024     │                        │
  │  │  strategy targets")       │                        │
  │  └───────────┬───────────────┘                        │
  │              │                                        │
  │              ▼  ToolMessage                           │
  │  "[Page 12 | Strategy] Keyboard segment               │
  │   target was 13,000 units..."                         │
  │              │                                        │
  │              ▼                                        │
  │     LLM thinks:                                       │
  │     "I have enough. Actual 12,450 vs target           │
  │      13,000 — I can now answer."                      │
  │          │                                            │
  │          ▼  AIMessage (no tool_calls) = DONE          │
  │  "In 2024, Rahul Technologies sold 12,450 keyboard    │
  │   units against a strategy target of 13,000..."       │
  └──────────────────────────────────────────────────────┘
       │
       ▼
  chat.py
  ├─ extract final AIMessage.content      → final_answer
  ├─ extract tool names from ToolMessages → tools_used
  ├─ build reasoning_log from thread      → step-by-step trace
  ├─ memory_store.add()                   → persist to session
  └─ return ChatResponse
       │
       ▼
  { "answer": "...", "intent": "BOTH",
    "tools_used": ["search_company_report", "analyse_company_sales"],
    "steps_taken": 2, "execution_time_ms": 3241 }
```

---

## Deep Agent Loop — How It Works

### `create_deep_agent` internals

The agent is built in `app/agent/graph.py` using:

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model=settings.model_name,          # "google_genai:gemini-flash-latest"
    tools=[search_company_report, analyse_company_sales],
    system_prompt=_system_prompt(conversation_summary),
)
```

Tools are **plain Python functions with docstrings** — no decorator needed. `create_deep_agent` reads the docstrings to build tool schemas for the LLM.

The loop:
```
  START
    │
    ▼
  agent  (calls the LLM with all messages so far)
    │
    ├── AIMessage has tool_calls? ──yes──► tools (executes tool, appends ToolMessage)
    │                                          │
    │                                          └──► back to agent
    │
    └── AIMessage has no tool_calls? ──► END
```

### System Prompt

Built in `graph.py → _system_prompt()`. Contains:
- Full built-in company knowledge (products, leadership, mission, etc.)
- Tool usage instructions (when to call each tool)
- Conversation summary (last 5 turns from session memory)
- Rules: don't call tools unnecessarily, don't repeat the same call, stop when done

---

## Tools

Defined in `app/agent/tools.py` as plain Python functions. `create_deep_agent` wraps them automatically using their docstrings.

### `search_company_report(query: str)`

Searches the in-memory PDF cache using keyword frequency scoring.

- Source: `rahul_technologies_corporate_report.pdf`
- Method: keyword tokenisation → score each cached chunk → return top 5
- Returns: formatted text with page numbers and section titles

### `analyse_company_sales(query: str)`

Analyses the in-memory Pandas DataFrame.

- Source: `Rahul_Technologies_Monthly_Production_and_Sales_2020_2025(1).xlsx`
- Columns: Year, Month (Jan–Dec), Category, Product, Produced, Sold
- Capabilities: totals, product breakdown, monthly/quarterly, YOY, MOM, CAGR, moving average, best/worst seller, category comparison

### When the LLM calls tools

| Question | Tool(s) called |
|----------|---------------|
| "What products do you manufacture?" | None — answered from system prompt knowledge |
| "Who is the CEO?" | None — answered from system prompt knowledge |
| "What are the 2025 expansion plans?" | `search_company_report` |
| "How many Gaming Keyboards sold in Q3 2024?" | `analyse_company_sales` |
| "Did 2024 sales meet the strategy targets?" | Both tools (LLM decides order) |
| "Compare keyboard vs mouse CAGR with report goals" | Both tools, potentially 2+ calls |

---

## Conversation Memory

`app/agent/memory.py` — `ConversationMemory` class.

- Stores up to **10 turns per session** (user + assistant pairs)
- Each `Turn` stores: user message, assistant answer, intent, tools used, timestamp
- `get_summary()` — formats last 5 turns as plain text → injected into system prompt
- `extract_context_hints()` — scans for last year and last product mentioned → used for coreference
- `list_sessions()` — returns all session metadata sorted by recency

**Coreference resolution** in `chat.py`:
```
Turn 1: "Show 2024 Gaming Mouse sales"   → last_year = 2024
Turn 2: "Compare with previous year"     → enriched to "... (referring to 2023)"
```

**Frontend persistence** — sessions stored in `localStorage` under `rt_agent_sessions`:
- Survives page refresh
- Max 10 sessions enforced, oldest deleted on overflow
- Server restart detected → `⚠️ memory reset` warning shown

---

## Retry & Rate Limit Handling

`app/agent/llm.py` — `run_with_retry()`.

An async helper for any direct LLM calls outside the agent graph. `create_deep_agent` handles its own internal retries via tenacity.

```
Attempt 1 fails (429) → wait 5s
Attempt 2 fails (429) → wait 10s
Attempt 3 fails (429) → wait 20s
Attempt 4 succeeds ✓
```

| Setting | Value |
|---------|-------|
| Max retries | 6 |
| Base delay | 5s |
| Backoff multiplier | ×2 |
| Max wait per retry | 60s |
| Jitter | ±2s |
| Frontend timeout | 120s |

---

## Data Caching Strategy

### PDF Cache (`app/knowledge/pdf_cache.py`)

Loaded once at startup via `startup.py → load_pdf()`:

1. `fitz.open()` — read all pages with PyMuPDF
2. `clean_text()` — normalise whitespace
3. Detect chapter title from first short line of each page
4. `chunk_text(chunk_size=800, overlap=150)` — overlapping word chunks
5. Store as `PDFChunk(chunk_id, text, page_number, chapter_title)`

Every `/chat` request searches `pdf_cache.chunks` in memory — disk is never touched again.

### Excel Cache (`app/tools/excel_sales_tool.py`)

Loaded once at startup via `startup.py → load_excel()`:

1. `pd.read_excel()` with `openpyxl`
2. Column normalisation → `year, month, category, product, units_produced, units_sold`
3. Add `month_num` (Jan=1 … Dec=12)
4. Store as `excel_cache.df`

Every `/chat` request runs `.groupby()` / `.sum()` etc. on `excel_cache.df` — disk is never touched again.

---

## Folder Structure

```
deep_agent/
│
├── app/
│   ├── api/
│   │   ├── chat.py          # POST /chat — Deep Agent entry point
│   │   ├── health.py        # GET /health, GET /agent/status
│   │   ├── sessions.py      # GET/DELETE /sessions
│   │   └── upload.py        # POST /upload/pdf, POST /upload/excel
│   │
│   ├── agent/
│   │   ├── graph.py         # create_deep_agent + system prompt builder
│   │   ├── tools.py         # Tool functions: search_company_report, analyse_company_sales
│   │   ├── llm.py           # run_with_retry() — async retry helper
│   │   └── memory.py        # Per-session ConversationMemory (max 10 turns)
│   │
│   ├── tools/
│   │   ├── pdf_reader.py        # Keyword search over cached PDF chunks
│   │   └── excel_sales_tool.py  # Pandas analysis functions
│   │
│   ├── knowledge/
│   │   ├── company_knowledge.py # Static company facts string
│   │   └── pdf_cache.py         # PDFCache singleton
│   │
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response models
│   │
│   ├── utils/
│   │   ├── config.py        # pydantic-settings from .env
│   │   ├── logger.py        # Structured JSON logger
│   │   └── helpers.py       # clean_text(), chunk_text()
│   │
│   ├── startup.py           # load_pdf() + load_excel() at boot
│   └── main.py              # FastAPI app + CORS + lifespan
│
├── frontend/
│   ├── demo.html            # ChatGPT-style UI
│   ├── styles.css           # Dark mode, responsive, animations
│   └── script.js            # Sessions, markdown, reasoning trace
│
├── data/
│   ├── rahul_technologies_corporate_report.pdf
│   └── Rahul_Technologies_Monthly_Production_and_Sales_2020_2025(1).xlsx
│
├── logs/
│   └── agent.log
│
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
└── README.md
```

---

## Installation

```bash
cd deep_agent
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Key dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.115.5 | Web framework |
| `uvicorn[standard]` | 0.32.1 | ASGI server |
| `deepagents` | 0.6.12 | `create_deep_agent` |
| `langchain-google-genai` | 4.2.6 | Gemini LLM integration |
| `pandas` | 2.2.3 | Excel data analysis |
| `PyMuPDF` | 1.25.1 | PDF parsing |
| `pydantic-settings` | 2.6.1 | `.env` config |

---

## Environment Variables

`.env` (based on `.env.example`):

```env
GOOGLE_API_KEY=your-google-api-key-here
MODEL_NAME=google_genai:gemini-flash-latest
TEMPERATURE=0.2
PDF_PATH=data/rahul_technologies_corporate_report.pdf
EXCEL_PATH=data/Rahul_Technologies_Monthly_Production_and_Sales_2020_2025(1).xlsx
```

All paths are relative to the `deep_agent/` directory where you run `uvicorn`.

---

## Running the Server

```bash
cd deep_agent
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Startup logs:
```json
{"level": "INFO", "message": "PDF loaded: rahul_technologies_corporate_report.pdf | pages=25 | chunks=87"}
{"level": "INFO", "message": "Excel loaded: ... | rows=720 | cols=['year', 'month', 'category', 'product', 'units_produced', 'units_sold', 'month_num']"}
```

---

## Running the Frontend

Open `frontend/demo.html` in your browser. No build step needed.

1. Set **Host** = `localhost`, **Port** = `8000`
2. Click **Connect** — shows `🟢 Connected` + model info toast
3. Start chatting

Each bot response shows:
- Intent badge (GENERAL / REPORT / SALES / BOTH)
- Tools used + execution time + step count
- Collapsible **🧠 Reasoning trace** — every tool call and observation

---

## API Reference

### POST /chat

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Did 2024 keyboard sales meet the strategy targets?", "session_id": "my-session"}'
```

```json
{
  "answer": "In 2024, Rahul Technologies sold X,XXX keyboard units...",
  "intent": "BOTH",
  "tools_used": ["search_company_report", "analyse_company_sales"],
  "execution_time_ms": 3241.5,
  "steps_taken": 2,
  "reasoning_log": [
    "Step 1 | TOOL CALL: analyse_company_sales | ARGS: {\"query\": \"keyboard units sold 2024\"}",
    "OBSERVATION (analyse_company_sales): ### Sales Analysis — 2024 ...",
    "Step 2 | TOOL CALL: search_company_report | ARGS: {\"query\": \"keyboard strategy targets 2024\"}",
    "OBSERVATION (search_company_report): [Page 12 | Strategy] ..."
  ]
}
```

### GET /health

```json
{"status": "healthy"}
```

### GET /agent/status

```json
{
  "model": "google_genai:gemini-flash-latest",
  "pdf_loaded": true,
  "pdf_chunks_count": 87,
  "excel_loaded": true,
  "excel_row_count": 720,
  "uptime_seconds": 142.3
}
```

### POST /upload/pdf

```bash
curl -X POST http://localhost:8000/upload/pdf -F "file=@new_report.pdf"
```

### POST /upload/excel

```bash
curl -X POST http://localhost:8000/upload/excel -F "file=@new_sales.xlsx"
```

---

## Session Management

### GET /sessions — list all sessions
### GET /sessions/{id} — full turn history
### DELETE /sessions/{id} — clear session memory

---

## Logs

`logs/agent.log` — newline-delimited JSON:

```json
{"timestamp": "...", "level": "INFO", "message": "PDF tool called: query='keyboard strategy 2024'"}
{"timestamp": "...", "level": "INFO", "message": "request_processed", "intent": "BOTH", "tools_selected": ["search_company_report", "analyse_company_sales"], "execution_time_ms": 3241.5}
```