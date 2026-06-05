# Capability Registry: Loader-SQLite-CSV

## Skill: `resolve_csv_source`
- **Description:** Resolves and validates the CSV source path against configured safe read roots.
- **Tools:** `smart_ingestion.utils.resolve_read_path`.
- **Execution:** Accept `source_path` -> Normalize relative path -> Enforce allowed roots -> Confirm file exists -> Return absolute path.

## Skill: `apply_transform_pipeline`
- **Description:** Loads source records and applies optional filter, join, and aggregate operations before persistence.
- **Tools:** `smart_ingestion.connectors.ingestion_pipeline.load_and_transform`.
- **Execution:** Load CSV rows -> Load join-side records when requested -> Apply filter -> Apply join -> Apply aggregate -> Return transformed records.

## Skill: `sanitize_sqlite_table_name`
- **Description:** Converts the requested table name into a SQLite-safe identifier.
- **Tools:** `smart_ingestion.utils.sanitize_table_name`.
- **Execution:** Strip unsupported characters -> Prefix leading digits when needed -> Reject empty results.

## Skill: `rebuild_sqlite_table`
- **Description:** Recreates the SQLite target table from the transformed row schema.
- **Tools:** Python `sqlite3`.
- **Execution:** Connect to target DB -> Drop existing table -> Create table with `TEXT` columns -> Prepare insert statement.

## Skill: `bulk_insert_transformed_rows`
- **Description:** Inserts the transformed dataset into SQLite using a deterministic column order.
- **Tools:** Python `sqlite3.executemany`.
- **Execution:** Extract column list from first row -> Build placeholder SQL -> Convert each row to ordered tuple -> Execute bulk insert -> Commit.

## Skill: `emit_ingestion_result`
- **Description:** Returns a structured success or failure payload to the orchestrator.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** Count inserted rows -> Attach final DB path -> Generate success message, or capture and surface exception text on failure.
