from smart_ingestion.agents.stream_json_base import StreamJsonAgentBase
from smart_ingestion.connectors.ingestion_pipeline import (
    needs_full_buffer,
    stream_collect_and_transform,
    stream_filter_record,
)
from smart_ingestion.connectors.stream_json import stream_options
from smart_ingestion.connectors.transforms import describe_transforms
from smart_ingestion.connectors.stream_json_writer import StreamingJsonWriter
from smart_ingestion.models import DestType, IngestionIntent, IngestionResult, PlanStep, SourceType
from smart_ingestion.utils import resolve_write_path


class StreamJsonToJsonAgent(StreamJsonAgentBase):
    agent_id = "stream_json_to_json"
    name = "Streaming JSON → JSON file"
    description = "Consume real-time JSON stream and persist as NDJSON or JSON array"
    required_fields: list[str] = []
    optional_fields = ["stream_url", "source_path", "dest_path", "options"]

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type == SourceType.STREAM_JSON and intent.dest_type == DestType.JSON_FILE:
            return 1.0
        if (intent.stream_url or (intent.source_path and ".ndjson" in intent.source_path)):
            if intent.dest_path and intent.dest_path.endswith((".json", ".ndjson", ".jsonl")):
                if "parquet" not in (intent.dest_path or "").lower():
                    return 0.85
        return 0.0

    def plan_steps(self, intent: IngestionIntent) -> list[PlanStep]:
        src = intent.stream_url or intent.source_path
        opts = stream_options(intent)
        fmt = opts["json_format"]
        return [
            PlanStep(order=1, title="Connect stream", description=f"Open JSON stream: {src}"),
            PlanStep(order=2, title="Stream records", description="Parse NDJSON/SSE events as they arrive"),
            PlanStep(
                order=3,
                title="Transform",
                description=describe_transforms(intent.transform),
            ),
            PlanStep(
                order=4,
                title="Write JSON output",
                description=f"Format: {fmt} → {intent.dest_path}",
            ),
        ]

    def execute(self, intent: IngestionIntent) -> IngestionResult:
        try:
            dest = resolve_write_path(intent.dest_path)  # type: ignore[arg-type]
            opts = stream_options(intent)
            fmt = opts["json_format"]
            if fmt not in ("ndjson", "json_array"):
                fmt = "ndjson"

            if fmt == "ndjson" and dest.suffix not in (".ndjson", ".jsonl"):
                dest = dest.with_suffix(".ndjson")

            writer = StreamingJsonWriter(dest, fmt=fmt)
            if needs_full_buffer(intent):
                for record in stream_collect_and_transform(intent):
                    writer.write_record(record)
            else:
                for record in self._iter_records(intent):
                    kept = stream_filter_record(intent, record)
                    if kept is not None:
                        writer.write_record(kept)

            rows = writer.close()
            if rows == 0:
                return IngestionResult(
                    success=False,
                    message="No records received from stream",
                    errors=["Stream was empty"],
                )

            return IngestionResult(
                success=True,
                message=f"Wrote {rows} streamed records to JSON ({fmt})",
                rows_processed=rows,
                output_location=str(dest),
            )
        except Exception as exc:
            return IngestionResult(
                success=False,
                message="Streaming JSON to JSON file failed",
                errors=[str(exc)],
            )
