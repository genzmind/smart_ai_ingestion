import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from smart_ingestion.config import STREAM_BATCH_SIZE
from smart_ingestion.utils import resolve_read_path


def _parse_json_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line or line.startswith(":"):
        return None
    if line.startswith("data:"):
        line = line[5:].strip()
    if line in ("[DONE]", ""):
        return None
    payload = json.loads(line)
    if isinstance(payload, dict):
        return payload
    return {"value": payload}


def iter_stream_records(
    *,
    source_path: str | None = None,
    stream_url: str | None = None,
    max_records: int | None = None,
    duration_seconds: float | None = None,
) -> Iterator[dict[str, Any]]:
    """
    Yield JSON objects from a real-time stream (HTTP/NDJSON/SSE) or NDJSON file.

    Stops when max_records or duration_seconds is reached (if set).
    """
    deadline = time.time() + duration_seconds if duration_seconds else None
    count = 0

    if source_path:
        path = resolve_read_path(source_path)
        with open(path, encoding="utf-8") as f:
            for line in f:
                if deadline and time.time() >= deadline:
                    break
                record = _parse_json_line(line)
                if record is None:
                    continue
                yield record
                count += 1
                if max_records and count >= max_records:
                    break
        return

    if not stream_url:
        raise ValueError("Either source_path (NDJSON file) or stream_url is required")

    if not stream_url.startswith(("http://", "https://")):
        raise ValueError("stream_url must start with http:// or https://")

    with httpx.Client(timeout=None) as client:
        with client.stream("GET", stream_url) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if deadline and time.time() >= deadline:
                    break
                if line is None:
                    continue
                record = _parse_json_line(line)
                if record is None:
                    continue
                yield record
                count += 1
                if max_records and count >= max_records:
                    break


def stream_options(intent) -> dict[str, Any]:
    opts = dict(intent.options or {})
    return {
        "batch_size": int(opts.get("batch_size", STREAM_BATCH_SIZE)),
        "max_records": opts.get("max_records"),
        "duration_seconds": opts.get("duration_seconds"),
        "json_format": opts.get("json_format", "ndjson"),
    }


def batched(iterator: Iterator[dict[str, Any]], batch_size: int) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for item in iterator:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
