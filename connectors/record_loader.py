import csv
import json
from pathlib import Path
from typing import Any

from smart_ingestion.utils import resolve_read_path


def load_records(path_str: str) -> list[dict[str, Any]]:
    path = resolve_read_path(path_str)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    if suffix in (".ndjson", ".jsonl"):
        records = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    if suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [r if isinstance(r, dict) else {"value": r} for r in data]
        raise ValueError("JSON file must be an array of objects for join/load")
    raise ValueError(f"Unsupported file type for load_records: {suffix}")
