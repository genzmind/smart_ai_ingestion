# Capability Registry: Loader-Postgres-CSV

## Skill: `resolve_postgres_target`
- **Description:** Determines the effective PostgreSQL connection target for the ingestion request.
- **Tools:** `smart_ingestion.config.DATABASE_URL`, request `database_url`.
- **Execution:** Prefer request override -> Fall back to configured URL -> Fail if no valid target exists.

## Skill: `read_csv_dataset`
- **Description:** Reads the full CSV dataset, including headers, before database write begins.
- **Tools:** Python `csv.DictReader`.
- **Execution:** Open CSV -> Parse header -> Materialize row dictionaries -> Return rows and ordered column names.

## Skill: `sanitize_destination_table`
- **Description:** Makes the table identifier safe for SQL execution.
- **Tools:** `smart_ingestion.utils.sanitize_table_name`.
- **Execution:** Strip unsupported characters -> Normalize leading digit case -> Reject invalid names.

## Skill: `recreate_postgres_table`
- **Description:** Creates a fresh PostgreSQL table based on CSV headers.
- **Tools:** `psycopg`, generated SQL DDL.
- **Execution:** Connect -> Drop table if exists -> Build `TEXT` column definitions -> Execute `CREATE TABLE`.

## Skill: `bulk_insert_postgres_rows`
- **Description:** Inserts all CSV rows into the recreated PostgreSQL table.
- **Tools:** `psycopg.executemany`.
- **Execution:** Build parameterized insert SQL -> Convert each CSV row to ordered value tuple -> Execute insert batch -> Commit.

## Skill: `redact_target_for_reporting`
- **Description:** Produces a user-safe database destination string for result reporting.
- **Tools:** simple connection-string parsing logic.
- **Execution:** Split on `@` when present -> Return host/database portion -> Avoid echoing credentials in the result message.
