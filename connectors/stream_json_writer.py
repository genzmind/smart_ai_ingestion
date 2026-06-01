import json
from pathlib import Path
from typing import Any


class StreamingJsonWriter:
    """
    Write streamed records to JSON.

    - ndjson: one JSON object per line (true streaming-friendly)
    - json_array: single JSON array file (written incrementally, closed at end)
    """

    def __init__(self, path: Path, fmt: str = "ndjson") -> None:
        self._path = path
        self._fmt = fmt
        self._rows = 0
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(self._path, "w", encoding="utf-8")
        if self._fmt == "json_array":
            self._file.write("[")

    def write_record(self, record: dict[str, Any]) -> None:
        if self._fmt == "ndjson":
            self._file.write(json.dumps(record, ensure_ascii=False) + "\n")
        else:
            if self._rows > 0:
                self._file.write(",\n")
            self._file.write(json.dumps(record, ensure_ascii=False))
        self._rows += 1

    def write_batch(self, records: list[dict[str, Any]]) -> None:
        for record in records:
            self.write_record(record)

    def close(self) -> int:
        if self._fmt == "json_array":
            self._file.write("]\n")
        self._file.close()
        return self._rows
