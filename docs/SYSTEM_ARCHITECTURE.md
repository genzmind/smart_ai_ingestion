# SMART AI Ingestion Tool - System Architecture

**Version:** 1.0  
**Date:** 2026-06-05

## 1. Purpose

This project is a chat-driven ingestion system that converts a natural-language request into a validated data movement plan, pauses for user confirmation, and then executes the selected ingestion pipeline.

The canonical runtime code lives under `src/smart_ingestion/`. The root-level `agents/` and `connectors/` folders are not part of the main application import path.

## 2. High-Level Architecture

```mermaid
flowchart TB
    U[User]
    B[Browser UI]
    API[FastAPI Application]
    ORCH[Orchestrator Service]
    SESS[Session Store]
    LLM[LLM Provider\nRule-based or OpenAI]
    REG[Agent Registry]

    subgraph AGENTS[Execution Agents]
        A1[Batch File/DB Agents]
        A2[REST -> JSON Agent]
        A3[Streaming JSON Agents]
    end

    subgraph PIPE[Connector Layer]
        RL[Record Loader]
        TF[Transform Pipeline]
        SJ[Streaming Source Reader]
        PW[Parquet Writer]
        JW[JSON Stream Writer]
        S3[S3 Connector]
        PG[PostgreSQL Connector]
    end

    subgraph STORAGE[Data + State Boundaries]
        TD[test_data/]
        UP[uploads/]
        OUT[data/output/]
        S3M[data/s3-mock/]
        DB1[SQLite]
        DB2[PostgreSQL]
        EXT[HTTP APIs / Streams]
    end

    U --> B
    B --> API
    API --> ORCH
    ORCH --> SESS
    ORCH --> LLM
    ORCH --> REG
    REG --> A1
    REG --> A2
    REG --> A3

    A1 --> RL
    A1 --> TF
    A1 --> DB1
    A1 --> DB2
    A1 --> S3

    A2 --> EXT
    A2 --> OUT

    A3 --> SJ
    A3 --> TF
    A3 --> PW
    A3 --> JW

    RL --> TD
    RL --> UP
    RL --> OUT
    RL --> S3M
    S3 --> S3M
```

## 3. Main Components

### 3.1 Presentation Layer

- `src/smart_ingestion/static/index.html`
- `src/smart_ingestion/static/app.js`
- `src/smart_ingestion/static/styles.css`

Responsibilities:

- Collect natural-language ingestion requests.
- Upload source files into `uploads/`.
- Display clarifying questions, plans, and execution results.
- Call `/api/chat`, `/api/confirm`, `/api/upload`, and `/api/agents`.

### 3.2 API Layer

- `src/smart_ingestion/main.py`

Responsibilities:

- Expose the FastAPI application.
- Serve the static chat UI.
- Persist uploads to `UPLOADS_DIR`.
- Route chat and confirmation requests to the orchestrator.

Endpoints:

- `GET /`
- `GET /api/health`
- `GET /api/agents`
- `POST /api/upload`
- `POST /api/chat`
- `POST /api/confirm`

### 3.3 Orchestration Layer

- `src/smart_ingestion/orchestrator.py`
- `src/smart_ingestion/session.py`
- `src/smart_ingestion/models.py`
- `src/smart_ingestion/transform_collector.py`

Responsibilities:

- Manage conversational session state.
- Merge new user input into an evolving `IngestionIntent`.
- Select the best ingestion agent through the registry.
- Ask for missing source, destination, or transform fields.
- Build an execution plan and require confirmation before side effects.
- Execute the chosen agent and return a structured result.

Session state machine:

```mermaid
stateDiagram-v2
    [*] --> idle
    idle --> collecting
    collecting --> awaiting_confirmation
    awaiting_confirmation --> executing
    awaiting_confirmation --> idle: cancel
    executing --> completed
    executing --> failed
    completed --> idle: next request
    failed --> idle: next request
```

### 3.4 Intent Extraction Layer

- `src/smart_ingestion/llm/factory.py`
- `src/smart_ingestion/llm/base.py`
- `src/smart_ingestion/llm/rule_based.py`
- `src/smart_ingestion/llm/openai_llm.py`
- `src/smart_ingestion/llm/transform_extract.py`

Responsibilities:

- Convert free-form user text into structured intent fields.
- Infer source type, destination type, paths, table names, stream URLs, and options.
- Extract requested transforms such as filter, join, and aggregate.
- Support a deterministic default parser and an optional OpenAI-backed provider.

### 3.5 Agent Layer

- `src/smart_ingestion/agents/base.py`
- `src/smart_ingestion/agents/registry.py`
- `src/smart_ingestion/agents/*.py`

Responsibilities:

- Encapsulate pipeline-specific matching, validation, planning, and execution.
- Provide a uniform contract: `matches()`, `validate()`, `build_plan()`, `execute()`.
- Keep side-effecting ingestion logic out of the orchestrator.

Current agent catalog:

| Agent ID | Flow |
|----------|------|
| `csv_to_sqlite` | CSV -> SQLite |
| `csv_to_postgresql` | CSV -> PostgreSQL |
| `csv_to_s3` | CSV -> S3 |
| `s3_to_sqlite` | S3 CSV -> SQLite |
| `json_to_sqlite` | JSON array -> SQLite |
| `rest_to_json` | REST API -> JSON file |
| `csv_to_csv` | CSV -> CSV |
| `stream_json_to_parquet` | Streaming JSON -> Parquet |
| `stream_json_to_json` | Streaming JSON -> JSON/NDJSON |

### 3.6 Connector Layer

- `src/smart_ingestion/connectors/record_loader.py`
- `src/smart_ingestion/connectors/ingestion_pipeline.py`
- `src/smart_ingestion/connectors/transforms.py`
- `src/smart_ingestion/connectors/stream_json.py`
- `src/smart_ingestion/connectors/parquet_writer.py`
- `src/smart_ingestion/connectors/stream_json_writer.py`
- `src/smart_ingestion/connectors/s3.py`
- `src/smart_ingestion/connectors/postgresql.py`

Responsibilities:

- Load source records from CSV, JSON, and NDJSON files.
- Apply filter, join, and aggregate transforms.
- Read streaming JSON from local NDJSON files or HTTP/SSE sources.
- Write outputs to Parquet, JSON, SQLite, PostgreSQL, and S3-backed storage.

## 4. Runtime Request Flow

### 4.1 Chat-to-plan flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Web UI
    participant API as FastAPI
    participant O as Orchestrator
    participant L as LLM Provider
    participant R as Agent Registry
    participant A as Selected Agent

    U->>UI: Describe ingestion request
    UI->>API: POST /api/chat
    API->>O: handle_message()
    O->>L: extract_intent()
    O->>R: select_best(intent)
    R-->>O: best matching agent
    O->>A: missing_fields() + validate()
    alt missing fields
        O-->>API: question response
        API-->>UI: ask follow-up
    else ready
        O->>A: build_plan()
        O-->>API: plan response
        API-->>UI: show confirm/cancel
    end
```

### 4.2 Confirm-to-execution flow

```mermaid
sequenceDiagram
    participant U as User
    participant UI as Web UI
    participant API as FastAPI
    participant O as Orchestrator
    participant A as Selected Agent
    participant C as Connectors / Sinks

    U->>UI: Confirm plan
    UI->>API: POST /api/confirm
    API->>O: handle_confirm()
    O->>A: execute(intent)
    A->>C: read, transform, write
    C-->>A: row counts / output path
    A-->>O: IngestionResult
    O-->>API: result response
    API-->>UI: completion or failure message
```

## 5. Data Processing Model

### 5.1 Intent model

The central contract is `IngestionIntent`, which carries:

- Source classification: `csv`, `json`, `rest`, `s3`, `stream_json`
- Destination classification: `sqlite`, `postgresql`, `s3`, `json_file`, `csv_file`, `parquet`
- Source and destination paths or URLs
- Table names and connection parameters
- Optional `options` for streaming controls
- Optional `transform` specification

The orchestrator incrementally merges partial user input into the same intent across turns.

### 5.2 Transform model

Transforms are applied in a fixed order:

```mermaid
flowchart LR
    SRC[Source records] --> FIL[Filter]
    FIL --> JN[Join]
    JN --> AGG[Aggregate]
    AGG --> DST[Destination sink]
```

Rules:

- `filter` can run per record or over a batch.
- `join` requires loading a right-side dataset from an allowed path.
- `aggregate` groups records and computes derived metrics.
- Streaming agents switch to full-buffer mode when join or aggregate is requested.

## 6. Storage and Integration Boundaries

Configured in `src/smart_ingestion/config.py` and enforced by `src/smart_ingestion/utils.py`.

Allowed read roots:

- `test_data/`
- `uploads/`
- `data/output/`
- `data/s3-mock/`

Allowed write roots:

- `uploads/`
- `data/output/`
- `data/s3-mock/`

External integrations:

- OpenAI API, when `LLM_PROVIDER=openai`
- HTTP REST APIs for `rest_to_json`
- HTTP/SSE/NDJSON streams for streaming agents
- PostgreSQL through configured connection URL
- AWS S3 or local mock S3 storage

## 7. Deployment View

Single-process default deployment:

```mermaid
flowchart LR
    CLIENT[Browser]
    APP[Uvicorn + FastAPI]
    FILES[Local filesystem]
    DB[(SQLite / PostgreSQL)]
    NET[External HTTP / OpenAI / S3]

    CLIENT --> APP
    APP --> FILES
    APP --> DB
    APP --> NET
```

Characteristics:

- Stateless API process except for in-memory session store.
- Session continuity depends on the current process instance.
- Best suited for local use, demos, and controlled single-node deployments.

## 8. Architectural Strengths and Constraints

Strengths:

- Clear separation between orchestration, agent selection, and execution logic.
- Confirmation gate prevents accidental side effects.
- Deterministic rule-based mode makes tests stable.
- Agent abstraction makes new pipelines straightforward to add.
- Path restrictions reduce unsafe file access.

Constraints:

- Session state is in-memory only and not shared across processes.
- Agent registry is static and instantiated at startup.
- Most batch connectors operate synchronously inside the API process.
- Transform execution is in-process and memory-bound for join/aggregate workloads.
- Runtime does not currently include a queue, worker pool, or persistent job tracking.

## 9. Extension Points

Recommended extension seams:

1. Add a new pipeline by implementing a new agent and registering it in `agents/registry.py`.
2. Add a new source or sink by introducing a connector and using it from an agent.
3. Improve intent extraction by extending `RuleBasedLLM` keywords or the OpenAI tool schema.
4. Replace the in-memory session store with a shared persistence layer for multi-instance deployment.
5. Move agent execution into background workers if long-running ingestion becomes a requirement.
