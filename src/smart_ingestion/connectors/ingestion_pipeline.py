from typing import Any

from smart_ingestion.connectors.record_loader import load_records
from smart_ingestion.connectors.stream_json import iter_stream_records, stream_options
from smart_ingestion.connectors.transforms import apply_filter, apply_transforms
from smart_ingestion.models import IngestionIntent


def needs_full_buffer(intent: IngestionIntent) -> bool:
    t = intent.transform
    if not t:
        return False
    if t.join:
        return True
    if t.aggregate and t.aggregate.metrics:
        return True
    return False


def load_and_transform(intent: IngestionIntent, records: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Load source records if needed, apply filter / join / aggregate pipeline."""
    data = records if records is not None else load_records(intent.source_path)  # type: ignore[arg-type]
    right: list[dict[str, Any]] | None = None
    if intent.transform and intent.transform.join and intent.transform.join.right_source_path:
        right = load_records(intent.transform.join.right_source_path)
    return apply_transforms(data, intent.transform, right)


def stream_collect_and_transform(intent: IngestionIntent) -> list[dict[str, Any]]:
    opts = stream_options(intent)
    max_records = opts["max_records"]
    if max_records is not None:
        max_records = int(max_records)
    duration = opts["duration_seconds"]
    if duration is not None:
        duration = float(duration)

    records = list(
        iter_stream_records(
            source_path=intent.source_path,
            stream_url=intent.stream_url,
            max_records=max_records,
            duration_seconds=duration,
        )
    )
    return load_and_transform(intent, records)


def stream_filter_record(intent: IngestionIntent, record: dict[str, Any]) -> dict[str, Any] | None:
    """Per-record filter when join/aggregate are not used."""
    t = intent.transform
    if not t or not t.filter or not t.filter.conditions:
        return record
    filtered = apply_filter([record], t.filter)
    return filtered[0] if filtered else None
