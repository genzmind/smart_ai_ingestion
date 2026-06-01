# SMART AI Ingestion Tool — Requirements Document

**Version:** 1.3  
**Date:** 2026-06-01  
**Status:** Approved for implementation

---

## 1. Executive Summary

The SMART AI Ingestion Tool is an intelligent data pipeline orchestrator. Users describe ingestion needs in natural language via a **chat bot** or **web UI**. An **LLM Orchestrator Agent** interprets the request, collects missing parameters, selects the appropriate **Data Ingestion Agent**, presents an **execution plan** for user confirmation, and runs the ingestion job.

---

## 2. Goals and Non-Goals

### 2.1 Goals

| ID | Goal |
|----|------|
| G1 | Accept natural-language ingestion requirements from chat or web UI |
| G2 | Automatically route work to the correct specialized ingestion agent |
| G3 | Prompt users for any missing required configuration before execution |
| G4 | Show a step-by-step plan and require explicit user confirmation |
| G5 | Support multiple **source** types and **destination** types (extensible) |
| G6 | Provide audit-friendly job results (status, rows affected, errors) |
| G7 | Support **real-time streaming JSON** ingestion to **Parquet** and **JSON** sinks |

### 2.2 Non-Goals (current release)

- Managed Kafka/Flink cluster operations (use HTTP/NDJSON/SSE streams or NDJSON files)
- Production-grade secrets vault (credentials via env / session only)
- Multi-tenant RBAC and billing
- Visual DAG editor for pipelines

---

## 3. Stakeholders and Users

| Role | Need |
|------|------|
| Data Analyst | Ingest CSV/Excel exports into a database without writing ETL code |
| Data Engineer | Prototype connectors, streaming sinks, and validate mappings quickly |
| Business User | Describe “load sales file into our DB” in plain English |
| Observability Engineer | Land live JSON events into Parquet lakes or JSON archives |

---

## 4. Functional Requirements

### 4.1 User Interface

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UI-01 | Web UI with chat-style conversation for ingestion requests | Must |
| FR-UI-02 | Display orchestrator questions when information is missing | Must |
| FR-UI-03 | Display execution plan (numbered steps) before running ingestion | Must |
| FR-UI-04 | Accept **Confirm** / **Cancel** for the proposed plan | Must |
| FR-UI-05 | Show job status and summary after completion | Must |
| FR-UI-06 | File upload for batch sources (CSV/JSON) | Should |

### 4.2 Orchestrator (LLM Agent)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ORCH-01 | Parse user intent: source type, destination type, paths, URLs, table name, stream options | Must |
| FR-ORCH-02 | Maintain conversation **session state** across turns | Must |
| FR-ORCH-03 | Detect **missing required fields** per selected agent schema | Must |
| FR-ORCH-04 | Ask clarifying questions one field or logical group at a time | Should |
| FR-ORCH-05 | Select exactly one ingestion agent from the registry when intent is clear | Must |
| FR-ORCH-06 | Generate human-readable **execution plan** with ordered steps | Must |
| FR-ORCH-07 | Support pluggable LLM backend (rule-based for dev/test, OpenAI-compatible for prod) | Should |

### 4.3 Data Ingestion Agents

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-AGENT-01 | Each agent declares: `agent_id`, description, required/optional parameters | Must |
| FR-AGENT-02 | Each agent implements `validate`, `plan_steps`, `execute` | Must |
| FR-AGENT-03 | Agents are registered in a central **registry** discoverable by orchestrator | Must |
| FR-AGENT-04 | Batch agents: CSV/JSON→SQLite, REST→JSON, CSV→CSV, CSV→PostgreSQL, CSV/S3, S3→SQLite | Must |
| FR-AGENT-05 | Streaming agents: **Streaming JSON→Parquet**, **Streaming JSON→JSON** | Must |
| FR-AGENT-06 | Execution returns structured result: success, message, rows_processed, output path | Must |

### 4.4 Sources and Destinations

| Source | Description |
|--------|-------------|
| Local file | Path under `test_data/`, `uploads/`, or `data/output/` |
| HTTP/REST | GET JSON (batch) |
| S3 | Object storage (AWS or local mock) |
| **Streaming JSON** | HTTP NDJSON/SSE endpoint or local `.ndjson`/`.jsonl` file (simulated stream) |

| Destination | Description |
|-------------|-------------|
| SQLite / PostgreSQL | Relational tables |
| JSON file | Batch array or streaming NDJSON / JSON array |
| CSV file | Transformed export |
| S3 | Object upload |
| **Parquet** | Columnar file built incrementally from stream batches |

### 4.5 Real-Time Streaming JSON (v1.2)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-STREAM-01 | Consume JSON events as a **stream** (line-delimited NDJSON or SSE `data:` lines) | Must |
| FR-STREAM-02 | Support **HTTP(S) stream URL** or **local NDJSON file** as source | Must |
| FR-STREAM-03 | Write **Parquet** output with batched row groups (configurable `batch_size`) | Must |
| FR-STREAM-04 | Write **JSON** output as **NDJSON** (line-per-event) or **JSON array** | Must |
| FR-STREAM-05 | Optional limits: `max_records`, `duration_seconds` for bounded runs/tests | Should |
| FR-STREAM-06 | Orchestrator routes phrases like “stream”, “real-time”, “NDJSON”, “Parquet” | Must |
| FR-STREAM-07 | User confirms execution plan before stream consumption starts | Must |

### 4.6 Conversation Flow

```
User request → Parse intent → Missing fields? 
    → Yes: Ask user → Update session → (repeat)
    → No: Select agent → Build plan → Show plan → Await confirmation
        → Confirmed: Execute agent → Report result
        → Cancelled: Reset to idle, acknowledge cancel
```

### 4.7 Data transforms (filter, join, aggregate)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-XFORM-01 | User can request **filter**, **join**, and/or **aggregate** in natural language | Must |
| FR-XFORM-02 | Orchestrator asks for missing transform parameters before showing the plan | Must |
| FR-XFORM-03 | Execution plan lists transforms (filter/join/aggregate) before ingestion | Must |
| FR-XFORM-04 | **Filter**: field, operator (eq, ne, gt, gte, lt, lte, in, contains), value | Must |
| FR-XFORM-05 | **Join**: right dataset path, `left_on`, `right_on`, join type (inner, left) | Must |
| FR-XFORM-06 | **Aggregate**: `group_by` columns, metrics (sum, count, avg, min, max) | Must |
| FR-XFORM-07 | Pipeline order: **filter → join → aggregate → ingest** | Must |
| FR-XFORM-08 | Streaming jobs buffer when join/aggregate require full dataset | Should |

### 4.8 Error Handling

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ERR-01 | Invalid file path → clear error, do not execute | Must |
| FR-ERR-02 | Schema/column mismatch → report row-level or batch error | Should |
| FR-ERR-03 | User cancel during plan review → no side effects | Must |
| FR-ERR-04 | Empty stream → fail with explicit message, no empty Parquet/JSON | Must |

---

## 5. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Performance | Batch single-file ingest &lt; 100k rows in 60s on dev hardware |
| NFR-02 | Streaming | Default batch size 50 records; configurable via intent `options` |
| NFR-03 | Security | No credentials in logs; stream URLs http/https only |
| NFR-04 | Testability | Rule-based LLM + NDJSON fixtures; no live stream required in CI |
| NFR-05 | Extensibility | New agent = registry entry + optional LLM keywords |
| NFR-06 | Observability | Structured logs per session; row counts in result |

---

## 6. Acceptance Criteria

1. User: *“Stream test_data/events.ndjson to Parquet at data/output/events.parquet”* → plan → confirm → Parquet file with 6 rows.
2. User: *“Ingest real-time JSON from test_data/events.ndjson to data/output/events.ndjson”* → NDJSON output with one object per line.
3. User omits destination path → orchestrator asks for `dest_path` before plan.
4. Automated tests pass without external LLM or live HTTP stream.
5. README documents streaming options (`batch_size`, `json_format`, etc.).

---

## 7. Glossary

| Term | Definition |
|------|------------|
| NDJSON | Newline-delimited JSON; one JSON object per line |
| SSE | Server-Sent Events; lines prefixed with `data:` |
| Streaming agent | Agent that reads records incrementally rather than loading full file into memory first |
| Parquet | Columnar storage format written via Apache Arrow |

---

## 8. Future Enhancements

- Kafka / Kinesis consumer agents
- Windowed aggregations on streams
- Schema registry integration (Avro/Protobuf)
- Snowflake / BigQuery streaming loads
