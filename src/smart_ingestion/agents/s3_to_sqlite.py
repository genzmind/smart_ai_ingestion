import csv
import sqlite3
from pathlib import Path

from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.config import DEFAULT_SQLITE_PATH, OUTPUT_DIR
from smart_ingestion.connectors.s3 import s3_storage
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import sanitize_table_name


class S3ToSqliteAgent(BaseIngestionAgent):
    agent_id = "s3_to_sqlite"
    name = "S3 → SQLite"
    description = "Download a CSV from S3 and load into SQLite"
    required_fields = ["s3_bucket", "s3_key", "table_name"]
    optional_fields = ["dest_path"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.S3 and intent.dest_type == DestType.SQLITE:
            return 1.0
        if intent.s3_bucket and intent.s3_key and intent.table_name and intent.dest_type == DestType.SQLITE:
            return 0.9
        return 0.0

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.s3_bucket:
            errors.append("s3_bucket is required")
        if not intent.s3_key:
            errors.append("s3_key is required")
        if not intent.table_name:
            errors.append("table_name is required")
        if intent.s3_key and not intent.s3_key.lower().endswith(".csv"):
            errors.append("s3_key must point to a .csv file for this agent")
        return errors

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        db = intent.dest_path or str(DEFAULT_SQLITE_PATH)
        return [
            PlanStep(
                order=1,
                title="Download from S3",
                description=f"s3://{intent.s3_bucket}/{intent.s3_key}",
            ),
            PlanStep(order=2, title="Parse CSV", description="Read columns and rows"),
            PlanStep(order=3, title="Load SQLite", description=f"Table '{intent.table_name}' in {db}"),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            temp_path = OUTPUT_DIR / f"_s3_dl_{intent.s3_key.replace('/', '_')}"  # type: ignore[union-attr]
            s3_storage.download_file(
                intent.s3_bucket,  # type: ignore[arg-type]
                intent.s3_key,  # type: ignore[arg-type]
                temp_path,
            )
            table = sanitize_table_name(intent.table_name)  # type: ignore[arg-type]
            db_path = intent.dest_path or str(DEFAULT_SQLITE_PATH)

            with open(temp_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if not rows:
                    return IngestionResult(success=False, message="CSV from S3 is empty", errors=["No rows"])
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

            Path(temp_path).unlink(missing_ok=True)

            return IngestionResult(
                success=True,
                message=f"Loaded {len(rows)} rows from S3 into SQLite table '{table}'",
                rows_processed=len(rows),
                output_location=db_path,
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="S3 to SQLite ingestion failed",
                errors=[str(exc)],
            )
