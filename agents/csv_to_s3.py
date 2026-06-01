from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.connectors.s3 import s3_storage
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import resolve_read_path


class CsvToS3Agent(BaseIngestionAgent):
    agent_id = "csv_to_s3"
    name = "CSV → S3"
    description = "Upload a local CSV file to an S3 bucket (or local S3 mock)"
    required_fields = ["source_path", "s3_bucket", "s3_key"]
    optional_fields = []

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.CSV and intent.dest_type == DestType.S3:
            return 1.0
        if intent.s3_bucket and intent.s3_key and intent.source_path:
            return 0.85
        return 0.0

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.source_path:
            errors.append("source_path is required")
        if not intent.s3_bucket:
            errors.append("s3_bucket is required")
        if not intent.s3_key:
            errors.append("s3_key is required")
        return errors

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        return [
            PlanStep(order=1, title="Validate CSV", description=f"Check {intent.source_path}"),
            PlanStep(
                order=2,
                title="Upload to S3",
                description=f"s3://{intent.s3_bucket}/{intent.s3_key}",
            ),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            source = resolve_read_path(intent.source_path)  # type: ignore[arg-type]
            location = s3_storage.upload_file(
                source,
                intent.s3_bucket,  # type: ignore[arg-type]
                intent.s3_key,  # type: ignore[arg-type]
            )
            row_count = sum(1 for _ in open(source, encoding="utf-8")) - 1
            return IngestionResult(
                success=True,
                message=f"Uploaded CSV to {location}",
                rows_processed=max(row_count, 0),
                output_location=location,
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="CSV to S3 upload failed",
                errors=[str(exc)],
            )
