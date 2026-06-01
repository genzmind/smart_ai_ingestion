from smart_ingestion.agents.base import BaseIngestionAgent
from smart_ingestion.connectors.stream_json import iter_stream_records, stream_options
from smart_ingestion.models import IngestionIntent, SourceType


class StreamJsonAgentBase(BaseIngestionAgent):
    """Shared validation for streaming JSON sources."""

    def matches(self, intent: IngestionIntent) -> float:
        if intent.source_type != SourceType.STREAM_JSON:
            return 0.0
        return 0.0  # subclasses override

    def missing_fields(self, intent: IngestionIntent) -> list[str]:
        missing = []
        if not intent.stream_url and not intent.source_path:
            missing.append("stream_url")
        if not intent.dest_path:
            missing.append("dest_path")
        return missing

    def validate(self, intent: IngestionIntent) -> list[str]:
        errors = []
        if not intent.stream_url and not intent.source_path:
            errors.append("Provide stream_url (HTTP/SSE/NDJSON endpoint) or source_path (NDJSON file)")
        if not intent.dest_path:
            errors.append("dest_path is required")
        if intent.stream_url and not intent.stream_url.startswith(("http://", "https://")):
            errors.append("stream_url must use http:// or https://")
        if intent.source_path and not (
            intent.source_path.endswith(".ndjson")
            or intent.source_path.endswith(".jsonl")
        ):
            errors.append("source_path for streaming must be a .ndjson or .jsonl file")
        return errors

    def field_prompt(self, field: str) -> str:
        prompts = {
            "stream_url": (
                "What is the streaming JSON URL? (NDJSON lines or SSE, e.g. "
                "https://example.com/events/stream)"
            ),
            "source_path": (
                "What is the path to the NDJSON stream file? (e.g. test_data/events.ndjson)"
            ),
            "dest_path": "Where should the output be saved? (e.g. data/output/events.parquet)",
        }
        return prompts.get(field, super().field_prompt(field))

    def _iter_records(self, intent: IngestionIntent):
        opts = stream_options(intent)
        max_records = opts["max_records"]
        if max_records is not None:
            max_records = int(max_records)
        duration = opts["duration_seconds"]
        if duration is not None:
            duration = float(duration)
        return iter_stream_records(
            source_path=intent.source_path,
            stream_url=intent.stream_url,
            max_records=max_records,
            duration_seconds=duration,
        )
