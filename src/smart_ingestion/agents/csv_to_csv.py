import csv

from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import resolve_read_path, resolve_write_path


class CsvToCsvAgent(BaseIngestionAgent):
    agent_id = "csv_to_csv"
    name = "CSV → CSV (transform)"
    description = "Read a CSV file, apply optional column filter, and write a new CSV"
    required_fields = ["source_path", "dest_path"]
    optional_fields = ["options"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.CSV and intent.dest_type == DestType.CSV_FILE:
            return 1.0
        if (
            intent.source_path
            and intent.dest_path
            and intent.source_path.endswith(".csv")
            and intent.dest_path.endswith(".csv")
        ):
            return 0.9
        return 0.0

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.source_path:
            errors.append("source_path is required")
        if not intent.dest_path:
            errors.append("dest_path is required")
        return errors

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        cols = intent.options.get("columns") if intent.options else None
        filter_desc = f"Keep columns: {cols}" if cols else "Copy all columns"
        return [
            PlanStep(order=1, title="Read source CSV", description=str(intent.source_path)),
            PlanStep(order=2, title="Transform", description=filter_desc),
            PlanStep(order=3, title="Write output", description=str(intent.dest_path)),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            source = resolve_read_path(intent.source_path)  # type: ignore[arg-type]
            dest = resolve_write_path(intent.dest_path)  # type: ignore[arg-type]
            keep_cols = intent.options.get("columns") if intent.options else None

            with open(source, newline="", encoding="utf-8") as f_in:
                reader = csv.DictReader(f_in)
                rows = list(reader)
                if not rows:
                    return IngestionResult(success=False, message="Source CSV is empty", errors=["No rows"])

                fieldnames = list(rows[0].keys())
                if keep_cols:
                    fieldnames = [c for c in keep_cols if c in fieldnames]

            with open(dest, "w", newline="", encoding="utf-8") as f_out:
                writer = csv.DictWriter(f_out, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow({k: row.get(k, "") for k in fieldnames})

            return IngestionResult(
                success=True,
                message=f"Wrote {len(rows)} rows to {dest}",
                rows_processed=len(rows),
                output_location=str(dest),
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="CSV to CSV transformation failed",
                errors=[str(exc)],
            )
