# 📚 Library Book Management System
### Powered by CrewAI + Claude Sonnet

A production-ready, multi-agent AI system for managing a library — built with [CrewAI](https://crewai.com) and Anthropic's **Claude Sonnet** as the underlying LLM. The system understands plain-English requests and routes them to the right specialist agent, which then calls the appropriate database tool and returns a structured, human-readable response.

---

## Table of Contents

1. [What This Project Does](#what-this-project-does)
2. [How It Works](#how-it-works)
3. [Project Structure](#project-structure)
4. [File-by-File Reference](#file-by-file-reference)
5. [Prerequisites](#prerequisites)
6. [Installation](#installation)
7. [Configuration](#configuration)
8. [Running the System](#running-the-system)
9. [Example Interactions](#example-interactions)
10. [Architecture Decisions](#architecture-decisions)
11. [Extending the System](#extending-the-system)
12. [Troubleshooting](#troubleshooting)

---

## What This Project Does

This system replaces a traditional library management interface with a conversational AI crew. Instead of navigating menus or filling forms, a librarian (or patron) types a natural-language request — and the AI handles it end-to-end.

**Core capabilities:**

| Capability | Example request |
|---|---|
| **Catalog search** | "Find books by George Orwell" |
| **Add new titles** | "Add Dune by Frank Herbert, ISBN 978-0-525-55360-5, Sci-Fi, 1965, 3 copies" |
| **Update records** | "Change the genre of book ID 4 to Non-Fiction" |
| **Check out a book** | "Check out '1984' for alice@example.com" |
| **Return a book** | "Return 'Sapiens' for bob@example.com" |
| **Overdue report** | "Show me all overdue loans" |
| **Personalised recommendations** | "Recommend a fantasy book for alice@example.com" |
| **Library statistics** | "Give me a full library report" |
| **Most borrowed** | "What are the top 5 most borrowed books?" |

The system ships with **8 pre-seeded books** and **2 demo members** so it works immediately after installation — no manual data entry required.

---

## How It Works

The system uses **CrewAI's hierarchical process**, which means a Manager LLM reads each incoming request, decides which specialist agent is best placed to handle it, and delegates accordingly. The specialist agent then enters a **ReAct loop** (Reason → Act → Observe) — it reasons about what tool to call, calls it, reads the result, and either returns a final answer or calls another tool.

```
User input (plain English)
        │
        ▼
  ┌─────────────────────────────┐
  │      Crew Manager (LLM)     │  ← classifies intent, assigns agent
  └─────────────────────────────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
  Cataloguer   Borrowing    Recommender  Report
    Agent       Manager       Agent      Analyst
        │           │           │           │
        ▼           ▼           ▼           ▼
  [search,      [checkout,   [by_genre,  [stats,
   add,          return,      history]    most_borrowed]
   update]       overdue]
        │           │           │           │
        └───────────┴───────────┴───────────┘
                        │
                        ▼
               SQLite Database
          (books · members · loans)
                        │
                        ▼
              Final response to user
```

Every tool returns a **JSON string**, giving the LLM structured data to reason over and quote accurately in its final response. All agents share one per-thread database connection (no open/close overhead per tool call) and one shared LLM instance (instantiated once at startup).

---

## Project Structure

```
library_crew/
│
├── main.py                   ← Entry point — run this to start the system
├── crew.py                   ← Crew assembly and request execution
├── requirements.txt          ← Python dependencies
├── .env.example              ← API key template
├── .gitignore
│
├── agents/
│   ├── __init__.py
│   ├── cataloguer.py         ← Catalog search, add, update
│   ├── borrowing_manager.py  ← Loans, returns, overdue
│   ├── recommender.py        ← Genre + history-based recommendations
│   └── report_analyst.py     ← Stats and ranked reports
│
├── tools/
│   ├── __init__.py
│   ├── catalog_tools.py      ← search_catalog, add_book, update_book
│   ├── borrowing_tools.py    ← checkout_book, return_book, list_overdue
│   ├── recommend_tools.py    ← books_by_genre, member_borrow_history
│   └── report_tools.py       ← library_stats, most_borrowed_books
│
└── db/
    ├── __init__.py
    ├── database.py           ← Connection pool, schema, seed data
    └── library.db            ← Created automatically on first run
```

---

## File-by-File Reference

### `main.py` — Entry Point
Loads the `.env` file, validates the API key (exits early with a clear message if missing), initialises the database, builds the crew once, then runs a REPL loop. Accepts plain-English input, passes it to `crew.run()`, and prints the response. Type `exit` or `quit` to stop.

### `crew.py` — Crew Assembly
Instantiates the shared `LLM` object (`claude-sonnet-4-6`, temperature `0.2` for deterministic tool-calling) and constructs all four agents by calling their builder functions. The `build_crew()` function should be called once at startup. The `run(crew, request)` function creates a fresh `Task` per request and calls `crew.kickoff()`.

### `db/database.py` — Database Layer
Manages a `threading.local()` connection pool — one persistent SQLite connection per thread, created on first access and reused for the lifetime of the process. Sets WAL mode, foreign key enforcement, and an 8 MB page cache per connection on creation. Defines the full schema (`books`, `members`, `loans`), creates optimised indexes (including a partial index on active loans), and seeds 8 books and 2 members on `init_db()`. Safe to call repeatedly — all DDL uses `IF NOT EXISTS`.

### `agents/cataloguer.py`
Manages all catalog operations. Equipped with `search_catalog`, `add_book`, and `update_book`. Has `allow_delegation=False` to prevent re-routing, `max_iter=5` to cap the ReAct loop, and `max_rpm=10` as a rate-limit guard.

### `agents/borrowing_manager.py`
Handles the full loan lifecycle. Equipped with `checkout_book`, `return_book`, and `list_overdue`. Configured identically to the Cataloguer in terms of iteration and rate limits.

### `agents/recommender.py`
Produces personalised book suggestions. Uses `books_by_genre` to filter available titles and `member_borrow_history` to understand a member's reading preferences before recommending.

### `agents/report_analyst.py`
Generates management-level insights. Uses `library_stats` (a single multi-aggregate SQL query for efficiency) and `most_borrowed_books` to surface trends.

### `tools/catalog_tools.py`
Three `@tool` functions: `search_catalog` does a `LIKE` match across title, author, genre, and ISBN; `add_book` validates `copies >= 1` before inserting; `update_book` validates the field name against an allowlist before updating, and re-syncs `available` when `copies` changes.

### `tools/borrowing_tools.py`
`checkout_book` is atomic — it inserts the loan and decrements `available` in a single transaction, with `rollback()` on any exception. `return_book` finds the most recent active loan for the member+ISBN pair. `list_overdue` uses SQLite's `julianday()` to compute days overdue server-side with the partial index on `returned_on IS NULL`.

### `tools/recommend_tools.py`
`books_by_genre` filters on `genre LIKE ?` so partial matches work (e.g. "Sci-Fi" matches "Science Fiction"). `member_borrow_history` returns all past loans ordered most-recent first for the recommender to reason over.

### `tools/report_tools.py`
`library_stats` runs a single SQL query with six sub-selects instead of six separate round-trips. `most_borrowed_books` uses a `GROUP BY` + `COUNT` aggregate ordered descending.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 – 3.12 | 3.13+ not yet supported by CrewAI |
| pip | Any current | Comes with Python |
| Anthropic API key | — | Get one free at [console.anthropic.com](https://console.anthropic.com) |
| Internet access | — | Required for LLM API calls |

> **macOS / Linux:** Python 3.10+ is usually available via your package manager or [pyenv](https://github.com/pyenv/pyenv).  
> **Windows:** Download from [python.org](https://python.org) and tick "Add Python to PATH" during install.

---

## Installation

Follow these steps exactly, in order.

### Step 1 — Unzip the project

```bash
unzip library_crew.zip
cd library_crew
```

### Step 2 — Check your Python version

```bash
python --version
# Must show 3.10, 3.11, or 3.12
```

If the version is below 3.10, upgrade before continuing.

### Step 3 — Create a virtual environment

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Your terminal prompt should now show `(.venv)` — confirming the environment is active.

> **Important:** Activate the virtual environment every time you open a new terminal session before running the project.

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `crewai[tools]` — the multi-agent framework and built-in tool integrations
- `anthropic` — the Anthropic Python SDK (used by CrewAI under the hood)
- `python-dotenv` — loads your `.env` file at startup

The first install may take **2–3 minutes** as CrewAI pulls in a large dependency tree (LangChain, tiktoken, etc.). This is normal.

---

## Configuration

### Step 5 — Set up your API key

Copy the example environment file:

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder with your real key:

```
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**Where to get your key:** Log in at [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key.

> **Security:** The `.env` file is listed in `.gitignore` and will never be included in a `git commit`. Never share or upload this file.

---

## Running the System

### Step 6 — Start the system

```bash
python main.py
```

On first run, the system will:
1. Validate your API key
2. Create `db/library.db` and run the schema migrations
3. Seed 8 books and 2 demo members
4. Build the crew and connect to the Anthropic API
5. Print the welcome banner and await your first request

**Expected startup output:**
```
╔══════════════════════════════════════════╗
║     Library Book Management System       ║
║        Powered by CrewAI + Claude        ║
╚══════════════════════════════════════════╝

[System] Initialising database ...
[DB] Ready → db/library.db
[System] Building crew (this takes a moment on first run) ...
[System] Ready.

You:
```

Type any request at the `You:` prompt and press Enter. The crew will process it and print the result. Type `exit` to quit.

---

## Example Interactions

Below are realistic requests you can try immediately after starting the system.

**Search the catalog:**
```
You: Find all science fiction books
```

**Check out a book:**
```
You: Check out 'Dune' for alice@example.com
```

**Return a book:**
```
You: Return 'Dune' for alice@example.com
```

**Get a recommendation:**
```
You: Recommend a book for bob@example.com based on what he's read before
```

**Add a new title:**
```
You: Add a new book — ISBN 978-0-7432-7357-2, title 'Animal Farm',
     author 'George Orwell', genre 'Dystopia', year 1945, 2 copies
```

**Update a record:**
```
You: Update the description of book ID 2 to 'Winston Smith's story of life under totalitarian rule'
```

**Overdue report:**
```
You: Which loans are overdue right now?
```

**Library statistics:**
```
You: Give me a full library report with all the key stats
```

**Most borrowed:**
```
You: What are the top 3 most borrowed books?
```

---

## Architecture Decisions

**Why `Process.hierarchical`?**  
With sequential processing, every request would run through every agent in order. Hierarchical lets the Manager LLM read the request and dispatch to exactly the right agent — faster, cheaper (fewer LLM calls), and more accurate.

**Why SQLite?**  
Zero-config, file-based, and sufficient for a single-library deployment. The WAL journal mode and partial indexes make it performant for concurrent reads. To scale to a multi-location deployment, swap `get_connection()` in `db/database.py` to use `psycopg2` or `SQLAlchemy` — the tool layer needs no other changes.

**Why one connection per thread?**  
Opening a new SQLite connection on every tool call (the naive approach) adds ~1ms of overhead per call and triggers unnecessary file-handle churn. The `threading.local()` pool creates the connection once per thread and reuses it, which matters when multiple agents call tools in rapid succession.

**Why temperature `0.2`?**  
Tool-calling reliability degrades at higher temperatures. At `0.2`, the LLM produces near-deterministic JSON arguments for tool calls — reducing the chance of malformed tool inputs that would cause a tool to return an error and force a retry.

**Why `max_iter=5` on agents?**  
Without an iteration cap, an agent that gets a confusing tool response can loop indefinitely. Five iterations is enough for any single request this system handles, and caps cost and latency on pathological inputs.

---

## Extending the System

### Add a new agent

1. Create `agents/my_agent.py` with a `build_my_agent(llm)` function following the same pattern as the existing agents.
2. Create `tools/my_tools.py` with one or more `@tool`-decorated functions.
3. Import and add the new agent to the `agents` list in `crew.py`.
4. Export the builder from `agents/__init__.py`.

### Add a new tool to an existing agent

1. Add the `@tool` function to the relevant file in `tools/`.
2. Import it in `tools/__init__.py`.
3. Add it to the `tools=[...]` list in the relevant agent builder.

### Swap to a different LLM

In `crew.py`, change the `model` parameter in `_build_llm()`:

```python
# OpenAI
return LLM(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"], temperature=0.2)

# Google Gemini
return LLM(model="gemini/gemini-1.5-pro", api_key=os.environ["GEMINI_API_KEY"], temperature=0.2)
```

Set the corresponding key in your `.env` file.

### Add member registration

Add an `add_member` tool to `tools/borrowing_tools.py`:

```python
@tool("add_member")
def add_member(name: str, email: str) -> str:
    """Register a new library member by name and email."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO members (name, email) VALUES (?, ?)", (name, email)
        )
        conn.commit()
        return _ok(member_id=cur.lastrowid, name=name, email=email)
    except Exception as exc:
        return _err(str(exc))
```

Then add it to the Borrowing Manager's `tools` list.

---

## Troubleshooting

**`ANTHROPIC_API_KEY is not set`**  
You either forgot to create `.env` from `.env.example`, or your terminal session doesn't have the virtual environment activated. Run `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows) and try again.

**`ModuleNotFoundError: No module named 'crewai'`**  
The virtual environment is not active. Activate it first (see Installation Step 3), then re-run.

**`python --version` shows 3.9 or below**  
CrewAI requires Python 3.10+. Install a newer version via [pyenv](https://github.com/pyenv/pyenv) (macOS/Linux) or [python.org](https://python.org) (Windows), then recreate the virtual environment.

**`sqlite3.OperationalError: database is locked`**  
This happens if two processes try to write to the database simultaneously. The system is designed for single-process use. If you need concurrent access, migrate to Postgres (see Architecture Decisions above).

**Agent loops without producing output**  
This can happen on very ambiguous requests. Add more specifics — for example, instead of "borrow a book", say "check out '1984' for alice@example.com". The crew uses the exact member email and book title to query the database.

**Slow first response**  
The first request in a session sends the full agent system prompts to the API. Subsequent requests in the same session reuse the built crew and are significantly faster.

**`pip install` fails on Windows with a build error**  
Some CrewAI dependencies require the Microsoft C++ Build Tools. Install them from [visualstudio.microsoft.com/visual-cpp-build-tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and retry.

---

## Demo Members and Books

The system seeds the following data on first run so you can test all features immediately.

**Members:**

| Name | Email |
|---|---|
| Alice Sharma | alice@example.com |
| Bob Rao | bob@example.com |

**Books (sample):**

| Title | Author | Genre | Copies |
|---|---|---|---|
| To Kill a Mockingbird | Harper Lee | Fiction | 3 |
| 1984 | George Orwell | Dystopia | 2 |
| The Great Gatsby | F. Scott Fitzgerald | Fiction | 2 |
| Sapiens | Yuval Noah Harari | Non-Fiction | 4 |
| Dune | Frank Herbert | Science Fiction | 3 |
| Atomic Habits | James Clear | Self-Help | 5 |
| The Name of the Wind | Patrick Rothfuss | Fantasy | 2 |
| Project Hail Mary | Andy Weir | Science Fiction | 3 |

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `crewai[tools]` | ≥ 0.80.0, < 1.0.0 | Multi-agent orchestration framework |
| `anthropic` | ≥ 0.40.0 | Anthropic Python SDK (Claude API) |
| `python-dotenv` | ≥ 1.0.0 | Loads `.env` file at startup |

SQLite is part of Python's standard library — no additional database installation required.

---

## License

This project is provided as a learning reference for Agentic AI development with CrewAI and Claude. Adapt freely for your own use cases.
