import sqlite3

from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.config import DEFAULT_SQLITE_PATH
from smart_ingestion.connectors.ingestion_pipeline import load_and_transform
from smart_ingestion.connectors.transforms import describe_transforms
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import sanitize_table_name


class CsvToSqliteAgent(BaseIngestionAgent):
    agent_id = "csv_to_sqlite"
    name = "CSV → SQLite"
    description = "Load a CSV file into a SQLite database table"
    required_fields = ["source_path", "table_name"]
    optional_fields = ["dest_path"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.CSV and intent.dest_type == DestType.SQLITE:
            return 1.0
        if intent.source_path and intent.source_path.endswith(".csv") and intent.table_name:
            return 0.9
        if "csv" in (intent.source_path or "").lower() and intent.dest_type == DestType.SQLITE:
            return 0.85
        return 0.0

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.source_path:
            errors.append("source_path is required")
        if not intent.table_name:
            errors.append("table_name is required")
        return errors

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        db = intent.dest_path or str(DEFAULT_SQLITE_PATH)
        steps = [
            PlanStep(order=1, title="Read CSV", description=f"Open and parse {intent.source_path}"),
            PlanStep(
                order=2,
                title="Transform",
                description=describe_transforms(intent.transform),
            ),
            PlanStep(
                order=3,
                title="Prepare SQLite",
                description=f"Connect to {db} and create/replace table '{intent.table_name}'",
            ),
            PlanStep(order=4, title="Insert rows", description="Bulk insert transformed records"),
            PlanStep(order=5, title="Commit", description="Finalize transaction and report row count"),
        ]
        return steps

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            table = sanitize_table_name(intent.table_name)  # type: ignore[arg-type]
            db_path = intent.dest_path or str(DEFAULT_SQLITE_PATH)

            rows = load_and_transform(intent)
            if not rows:
                    return IngestionResult(
                        success=False,
                        message="CSV file is empty",
                        errors=["No data rows found"],
                    )
                columns = list(rows[0].keys())

            conn = sqlite3.connect(db_path)
            try:
                col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')
                conn.execute(f'CREATE TABLE "{table}" ({col_defs})')
                placeholders = ", ".join("?" for _ in columns)
                col_names = ", ".join(f'"{c}"' for c in columns)
                insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'
                values = [tuple(row.get(c, "") for c in columns) for row in rows]
                conn.executemany(insert_sql, values)
                conn.commit()
            finally:
                conn.close()

            return IngestionResult(
                success=True,
                message=f"Successfully loaded {len(rows)} rows into table '{table}'",
                rows_processed=len(rows),
                output_location=db_path,
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="CSV to SQLite ingestion failed",
                errors=[str(exc)],
            )
