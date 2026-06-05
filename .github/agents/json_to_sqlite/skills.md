# Capability Registry: Loader-SQLite-JSON

## Skill: `load_json_and_transforms`
- **Description:** Loads the JSON source and applies the shared transform pipeline before persistence.
- **Tools:** `smart_ingestion.connectors.ingestion_pipeline.load_and_transform`.
- **Execution:** Resolve source path -> Load JSON array -> Apply filter -> Apply join if requested -> Apply aggregate if requested -> Return transformed records.

## Skill: `derive_union_schema`
- **Description:** Builds the destination column list from all transformed object keys.
- **Tools:** Python iteration over dictionaries.
- **Execution:** Scan every transformed record -> Preserve first-seen key order -> Accumulate unique keys -> Reject empty schema.

## Skill: `normalize_destination_table`
- **Description:** Converts the requested table name into a SQLite-safe identifier.
- **Tools:** `smart_ingestion.utils.sanitize_table_name`.
- **Execution:** Strip invalid characters -> Handle leading digits -> Reject empty output.

## Skill: `serialize_records_for_sqlite`
- **Description:** Converts transformed JSON objects into ordered row tuples for insertion.
- **Tools:** Python `str()` conversion and tuple construction.
- **Execution:** For each column -> Read field from object -> Default missing values to empty string -> Stringify complex values -> Emit tuple.

## Skill: `materialize_sqlite_table`
- **Description:** Recreates the SQLite table and inserts the transformed records.
- **Tools:** Python `sqlite3`.
- **Execution:** Open DB -> Drop old table -> Create `TEXT` columns -> Bulk insert serialized tuples -> Commit.

## Skill: `emit_json_load_result`
- **Description:** Returns the final outcome to the orchestrator.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** Count inserted rows -> Attach DB path -> Produce success message, or propagate failure reason.
