# Capability Registry: Loader-SQLite-S3

## Skill: `download_s3_object_to_stage`
- **Description:** Retrieves the target CSV object from S3-compatible storage into a controlled temporary local file.
- **Tools:** `smart_ingestion.connectors.s3.s3_storage.download_file`.
- **Execution:** Build temp path -> Download object bytes -> Confirm staged file exists -> Return staged path.

## Skill: `parse_staged_csv`
- **Description:** Reads the staged CSV file into memory for SQLite loading.
- **Tools:** Python `csv.DictReader`.
- **Execution:** Open staged file -> Extract headers -> Materialize row dictionaries -> Reject empty datasets.

## Skill: `prepare_sqlite_target`
- **Description:** Sanitizes the destination table name and prepares a writable SQLite destination.
- **Tools:** `smart_ingestion.utils.sanitize_table_name`, Python `sqlite3`.
- **Execution:** Normalize table name -> Resolve DB path -> Open SQLite connection.

## Skill: `recreate_and_load_table`
- **Description:** Drops and recreates the SQLite table, then inserts all staged CSV rows.
- **Tools:** Python `sqlite3`.
- **Execution:** Build `TEXT` column DDL -> Execute `DROP TABLE IF EXISTS` -> Execute `CREATE TABLE` -> Perform ordered `executemany` insert -> Commit.

## Skill: `cleanup_staged_download`
- **Description:** Removes the temporary downloaded CSV after a successful load.
- **Tools:** `pathlib.Path.unlink`.
- **Execution:** Resolve staged file path -> Delete file with missing-ok semantics.

## Skill: `return_load_result`
- **Description:** Reports the final outcome back to the orchestrator.
- **Tools:** `smart_ingestion.models.IngestionResult`.
- **Execution:** Count inserted rows -> Attach SQLite DB path -> Produce success message, or include surfaced exception text on failure.
