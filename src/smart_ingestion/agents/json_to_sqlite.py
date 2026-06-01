import json
import sqlite3

from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.config import DEFAULT_SQLITE_PATH
from smart_ingestion.connectors.ingestion_pipeline import load_and_transform
from smart_ingestion.connectors.transforms import describe_transforms
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import sanitize_table_name


class JsonToSqliteAgent(BaseIngestionAgent):
    agent_id = "json_to_sqlite"
    name = "JSON → SQLite"
    description = "Load a JSON array file into a SQLite database table"
    required_fields = ["source_path", "table_name"]
    optional_fields = ["dest_path"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.JSON and intent.dest_type == DestType.SQLITE:
            return 1.0
        if intent.source_path and intent.source_path.endswith(".json") and intent.table_name:
            return 0.9
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
        return [
            PlanStep(order=1, title="Read JSON", description=f"Parse array from {intent.source_path}"),
            PlanStep(order=2, title="Transform", description=describe_transforms(intent.transform)),
            PlanStep(order=3, title="Infer schema", description="Derive columns from transformed records"),
            PlanStep(order=4, title="Load SQLite", description=f"Write to {db}, table '{intent.table_name}'"),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            table = sanitize_table_name(intent.table_name)  # type: ignore[arg-type]
            db_path = intent.dest_path or str(DEFAULT_SQLITE_PATH)

            data = load_and_transform(intent)
            if not data:
                return IngestionResult(success=False, message="No records after load/transform", errors=["Empty"])

            columns: list[str] = []
            for item in data:
                if isinstance(item, dict):
                    for key in item:
                        if key not in columns:
                            columns.append(key)
            if not columns:
                return IngestionResult(
                    success=False,
                    message="No object keys found in JSON records",
                    errors=["Invalid JSON structure"],
                )

            conn = sqlite3.connect(db_path)
            try:
                col_defs = ", ".join(f'"{c}" TEXT' for c in columns)
                conn.execute(f'DROP TABLE IF EXISTS "{table}"')
                conn.execute(f'CREATE TABLE "{table}" ({col_defs})')
                placeholders = ", ".join("?" for _ in columns)
                col_names = ", ".join(f'"{c}"' for c in columns)
                insert_sql = f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'
                values = [
                    tuple(str(item.get(c, "")) if isinstance(item, dict) else "" for c in columns)
                    for item in data
                ]
                conn.executemany(insert_sql, values)
                conn.commit()
            finally:
                conn.close()

            return IngestionResult(
                success=True,
                message=f"Loaded {len(data)} JSON records into '{table}'",
                rows_processed=len(data),
                output_location=db_path,
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="JSON to SQLite ingestion failed",
                errors=[str(exc)],
            )
