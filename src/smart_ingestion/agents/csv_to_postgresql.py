from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.config import DATABASE_URL
from smart_ingestion.connectors.postgresql import load_csv_to_postgresql
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import resolve_read_path


class CsvToPostgresqlAgent(BaseIngestionAgent):
    agent_id = "csv_to_postgresql"
    name = "CSV → PostgreSQL"
    description = "Load a CSV file into a PostgreSQL table"
    required_fields = ["source_path", "table_name"]
    optional_fields = ["database_url"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.CSV and intent.dest_type == DestType.POSTGRESQL:
            return 1.0
        if "postgres" in (intent.database_url or "").lower():
            return 0.9
        return 0.0

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.source_path:
            errors.append("source_path is required")
        if not intent.table_name:
            errors.append("table_name is required")
        if not (intent.database_url or DATABASE_URL):
            errors.append("database_url is required (set DATABASE_URL env or provide in chat)")
        return errors

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        db = intent.database_url or DATABASE_URL
        redacted = db.split("@")[-1] if "@" in db else "configured database"
        return [
            PlanStep(order=1, title="Read CSV", description=f"Parse {intent.source_path}"),
            PlanStep(order=2, title="Connect PostgreSQL", description=f"Target: {redacted}"),
            PlanStep(
                order=3,
                title="Load table",
                description=f"Create/replace table '{intent.table_name}' and insert rows",
            ),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            source = resolve_read_path(intent.source_path)  # type: ignore[arg-type]
            count = load_csv_to_postgresql(
                str(source),
                intent.table_name,  # type: ignore[arg-type]
                intent.database_url,
            )
            db = intent.database_url or DATABASE_URL
            return IngestionResult(
                success=True,
                message=f"Loaded {count} rows into PostgreSQL table '{intent.table_name}'",
                rows_processed=count,
                output_location=db.split("@")[-1] if "@" in db else db,
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="CSV to PostgreSQL ingestion failed",
                errors=[str(exc)],
            )
