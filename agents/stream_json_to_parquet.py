from smart_ingestion.agents.stream_json_base import StreamJsonAgentBase
from smart_ingestion.connectors.ingestion_pipeline import (
    needs_full_buffer,
    stream_collect_and_transform,
    stream_filter_record,
)
from smart_ingestion.connectors.parquet_writer import StreamingParquetWriter
from smart_ingestion.connectors.stream_json import batched, stream_options
from smart_ingestion.connectors.transforms import describe_transforms
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import resolve_write_path


class StreamJsonToParquetAgent(StreamJsonAgentBase):
    agent_id = "stream_json_to_parquet"
    name = "Streaming JSON → Parquet"
    description = "Consume real-time JSON (HTTP/SSE/NDJSON) and write columnar Parquet output"
    required_fields: list[str] = []
    optional_fields = ["stream_url", "source_path", "dest_path", "options"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.STREAM_JSON and intent.dest_type == DestType.PARQUET:
            return 1.0
        if intent.dest_path and intent.dest_path.endswith(".parquet"):
            if intent.stream_url or (
                intent.source_path
                and intent.source_path.endswith((".ndjson", ".jsonl"))
            ):
                return 0.9
        return 0.0

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        src = intent.stream_url or intent.source_path
        opts = stream_options(intent)
        return [
            PlanStep(order=1, title="Connect stream", description=f"Open JSON stream: {src}"),
            PlanStep(
                order=2,
                title="Consume records",
                description="Read events in real time (NDJSON/SSE lines)",
            ),
            PlanStep(
                order=3,
                title="Transform",
                description=describe_transforms(intent.transform),
            ),
            PlanStep(
                order=4,
                title="Batch & write Parquet",
                description=f"Flush every {opts['batch_size']} rows to {intent.dest_path}",
            ),
            PlanStep(order=5, title="Finalize", description="Close Parquet writer and report row count"),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            dest = resolve_write_path(intent.dest_path)  # type: ignore[arg-type]
            if dest.suffix.lower() != ".parquet":
                dest = dest.with_suffix(".parquet")

            opts = stream_options(intent)
            writer = StreamingParquetWriter(dest)

            if needs_full_buffer(intent):
                records = stream_collect_and_transform(intent)
                for batch in batched(iter(records), opts["batch_size"]):
                    writer.write_batch(batch)
            else:
                batch: list = []
                for record in self._iter_records(intent):
                    kept = stream_filter_record(intent, record)
                    if kept is None:
                        continue
                    batch.append(kept)
                    if len(batch) >= opts["batch_size"]:
                        writer.write_batch(batch)
                        batch = []
                if batch:
                    writer.write_batch(batch)

            rows = writer.close()
            if rows == 0:
                return IngestionResult(
                    success=False,
                    message="No records received from stream",
                    errors=["Stream was empty or ended before any JSON objects were parsed"],
                )

            return IngestionResult(
                success=True,
                message=f"Streamed {rows} JSON records into Parquet",
                rows_processed=rows,
                output_location=str(dest),
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="Streaming JSON to Parquet failed",
                errors=[str(exc)],
            )
