# SMART AI Ingestion Tool

Intelligent data ingestion orchestrator: describe your pipeline in natural language, get clarifying questions when needed, review an execution plan, and confirm before any data is moved.

## Features

- **Chat / Web UI** for natural-language ingestion requests
- **LLM Orchestrator** (rule-based by default; pluggable for OpenAI later) routes to the right agent
- **Missing-field prompts** before planning
- **Execution plan + Confirm/Cancel** before side effects
- **Specialized agents**: CSV→SQLite, JSON→SQLite, REST→JSON, CSV→CSV, CSV→PostgreSQL, CSV→S3, S3→SQLite
- **Streaming JSON** → **Parquet** or **JSON** (NDJSON / JSON array) from HTTP/SSE or `.ndjson` files
- **File upload** in the Web UI (`uploads/` folder)
- **OpenAI orchestrator** with tool-calling (optional; rule-based default)

## Documentation

| Document | Path |
|----------|------|
| Requirements | [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) |
| Design | [docs/DESIGN.md](docs/DESIGN.md) |
| System Architecture | [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) |

## Quick start

```powershell
cd "c:\sweta\Smart ingestion"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn smart_ingestion.main:app --reload --app-dir src
```

Open **http://127.0.0.1:8000** in your browser.

Copy `.env.example` to `.env` to configure PostgreSQL, S3, or OpenAI.

### OpenAI orchestrator

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

The orchestrator uses tool-calling (`set_ingestion_intent`) and falls back to rule-based parsing if the API is unavailable.

### S3 (local mock by default)

With `S3_USE_LOCAL=true` (default), files are stored under `data/s3-mock/` — no AWS account required.

For real S3, set `S3_USE_LOCAL=false` and configure AWS credentials.

### PostgreSQL

Start PostgreSQL and set `DATABASE_URL`, then:

`Load test_data/customers.csv into PostgreSQL table customers`

Live PG tests: `RUN_POSTGRES_TESTS=true pytest tests/test_postgresql_agent.py`

## Example conversation

1. **You:** `Load test_data/customers.csv into SQLite table customers`
2. **Bot:** Shows execution plan (4 steps) and Confirm/Cancel buttons
3. **You:** Click **Confirm plan**
4. **Bot:** `Ingestion complete` — 5 rows in `data/output/ingestion.db`

If you omit the table name:

1. **You:** `Load test_data/customers.csv into SQLite`
2. **Bot:** `What should the SQLite table name be?`
3. **You:** `customers`
4. **Bot:** Plan → confirm → run

## Test data

| File | Description |
|------|-------------|
| `test_data/customers.csv` | 5 customer records |
| `test_data/products.json` | 4 product records (JSON array) |
| `test_data/events.ndjson` | 6 streaming event records (NDJSON) |

### Streaming JSON examples

```
Stream test_data/events.ndjson to Parquet at data/output/events.parquet
```

```
Stream test_data/events.ndjson to data/output/events.ndjson
```

Optional intent `options` (via chat or future UI):

| Option | Description |
|--------|-------------|
| `batch_size` | Parquet flush interval (default 50) |
| `max_records` | Stop after N events |
| `duration_seconds` | Stop after elapsed seconds |
| `json_format` | `ndjson` or `json_array` for JSON sink |

HTTP live stream: provide `stream_url` instead of `source_path` (NDJSON or SSE).

Outputs are written under `data/output/` (gitignored).

## Run tests

```powershell
.\.venv\Scripts\activate
pip install -r requirements.txt
pytest -v
```

Tests use a **rule-based LLM** (no API key). REST API agent tests are optional in CI if network is blocked; core E2E uses local CSV/SQLite only.

## Project structure

```
docs/                  Requirements & design
src/smart_ingestion/   Application code
  agents/              Ingestion agents + registry
  llm/                 Intent extraction
  static/              Web UI
test_data/             Sample source files
tests/                 Pytest suite
```

## Extending

1. Subclass `BaseIngestionAgent` in `src/smart_ingestion/agents/`
2. Register in `agents/registry.py`
3. Add keywords to `llm/rule_based.py` (or wire OpenAI structured output)

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web UI |
| `/api/chat` | POST | Send user message |
| `/api/confirm` | POST | `{ session_id, confirmed }` |
| `/api/agents` | GET | List agents |
| `/api/upload` | POST | Multipart file upload → `uploads/` |
| `/api/health` | GET | Health check (+ `llm_provider`) |
