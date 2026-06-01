import re

from smart_ingestion.llm.base import LLMProvider
from smart_ingestion.llm.transform_extract import extract_transforms
from smart_ingestion.models import DestType, IngestionIntent, SourceType


class RuleBasedLLM(LLMProvider):
    """Deterministic intent parser for development and automated tests."""

    def extract_intent(
        self,
        message: str,
        current: IngestionIntent,
        history: list[tuple[str, str]] | None = None,
    ) -> IngestionIntent:
        text = message.strip()
        lower = text.lower()
        updates = IngestionIntent()

        if re.search(r"\bcsv\b", lower) and "json" not in lower:
            if "postgres" in lower or "postgresql" in lower:
                updates.source_type = SourceType.CSV
                updates.dest_type = DestType.POSTGRESQL
            elif "s3" in lower or "bucket" in lower:
                updates.source_type = SourceType.CSV
                updates.dest_type = DestType.S3
            elif "sqlite" in lower:
                updates.source_type = SourceType.CSV
                updates.dest_type = DestType.SQLITE
            elif ("database" in lower or " db" in lower) and "postgres" not in lower:
                updates.source_type = SourceType.CSV
                updates.dest_type = DestType.SQLITE
            elif re.search(r"\bto\b.*\bcsv\b", lower) or "transform" in lower:
                updates.source_type = SourceType.CSV
                updates.dest_type = DestType.CSV_FILE
            elif updates.source_type == SourceType.UNKNOWN:
                updates.source_type = SourceType.CSV

        is_stream = any(
            k in lower for k in ("stream", "streaming", "real-time", "realtime", "sse", "ndjson")
        )
        if is_stream and "json" in lower:
            updates.source_type = SourceType.STREAM_JSON
            if "parquet" in lower:
                updates.dest_type = DestType.PARQUET
            elif "json" in lower:
                updates.dest_type = DestType.JSON_FILE
            if "ndjson" in lower:
                updates.options = {**updates.options, "json_format": "ndjson"}
            if "json array" in lower or "json_array" in lower:
                updates.options = {**updates.options, "json_format": "json_array"}

        if "json" in lower and updates.source_type != SourceType.STREAM_JSON:
            if "sqlite" in lower or "database" in lower:
                updates.source_type = SourceType.JSON
                updates.dest_type = DestType.SQLITE
            elif "file" in lower or "save" in lower:
                updates.source_type = SourceType.JSON
                updates.dest_type = DestType.JSON_FILE

        if any(k in lower for k in ("api", "rest", "http", "endpoint", "fetch")):
            if updates.source_type != SourceType.STREAM_JSON:
            updates.source_type = SourceType.REST
            updates.dest_type = DestType.JSON_FILE

        if "sqlite" in lower and updates.dest_type == DestType.UNKNOWN:
            updates.dest_type = DestType.SQLITE

        if re.search(r"\bs3\b", lower) and ("from s3" in lower or "s3://" in lower):
            updates.source_type = SourceType.S3
            if "sqlite" in lower:
                updates.dest_type = DestType.SQLITE

        s3_uri = re.search(r"s3://([\w.-]+)/(.+)", text, re.IGNORECASE)
        if s3_uri:
            updates.s3_bucket = s3_uri.group(1)
            updates.s3_key = s3_uri.group(2).rstrip(".,)")
            updates.source_type = SourceType.S3

        bucket_match = re.search(r"bucket\s+['\"]?([\w.-]+)['\"]?", lower)
        key_match = re.search(r"(?:key|object)\s+['\"]?([\w./-]+)['\"]?", lower)
        if bucket_match:
            updates.s3_bucket = bucket_match.group(1)
        if key_match:
            updates.s3_key = key_match.group(1)

        if "postgres" in lower and updates.dest_type == DestType.UNKNOWN:
            updates.dest_type = DestType.POSTGRESQL

        path_match = re.search(
            r"([\w./\\-]+\.(?:csv|json|ndjson|jsonl|parquet))",
            text,
            re.IGNORECASE,
        )
        if path_match:
            path_val = path_match.group(1).replace("\\", "/")
            if path_val.endswith((".ndjson", ".jsonl")):
                updates.source_type = SourceType.STREAM_JSON
                updates.source_path = path_val
            else:
                updates.source_path = path_val

        url_match = re.search(r"https?://[^\s]+", text)
        if url_match:
            url = url_match.group(0).rstrip(".,)")
            if updates.source_type == SourceType.STREAM_JSON or is_stream:
                updates.stream_url = url
            else:
                updates.api_url = url

        parquet_dest = re.search(
            r"(?:to|into|save(?:\s+as)?|output)\s+['\"]?([\w./\\-]+\.parquet)['\"]?",
            lower,
        )
        if parquet_dest:
            updates.dest_path = parquet_dest.group(1).replace("\\", "/")
            updates.dest_type = DestType.PARQUET

        reserved = {"sqlite", "postgresql", "postgres", "database", "db", "table", "json", "csv", "file", "s3"}
        table_patterns = [
            r"table\s+['\"]?(\w+)['\"]?",
            r"into\s+(?:sqlite|postgresql|postgres)\s+(?:table\s+)?['\"]?(\w+)['\"]?",
            r"(?:sqlite|postgresql)\s+table\s+['\"]?(\w+)['\"]?",
            r"into\s+(?:table\s+)?['\"]?(\w+)['\"]?",
        ]
        for pattern in table_patterns:
            m = re.search(pattern, lower)
            if m and m.group(1) not in reserved:
                updates.table_name = m.group(1)
                break

        dest_file = re.search(
            r"(?:to|into|save(?:\s+as)?|output)\s+['\"]?([\w./\\-]+\.(?:json|ndjson|jsonl|csv|parquet))['\"]?",
            lower,
        )
        if dest_file:
            updates.dest_path = dest_file.group(1).replace("\\", "/")

        if updates.dest_type == DestType.JSON_FILE and not updates.dest_path:
            if "output" in lower:
                updates.dest_path = "data/output/api_response.json"

        if self._looks_like_path_only(text):
            if text.endswith((".ndjson", ".jsonl")):
                updates.source_type = SourceType.STREAM_JSON
                updates.source_path = text.replace("\\", "/")
            elif text.endswith(".csv") or text.endswith(".json"):
                updates.source_path = text.replace("\\", "/")
            elif text.startswith("http"):
                if current.source_type == SourceType.STREAM_JSON:
                    updates.stream_url = text
                else:
                    updates.api_url = text
            elif re.match(r"^[\w_]+$", text) and current.table_name is None:
                updates.table_name = text

        if "uploads/" in lower and not updates.source_path:
            up = re.search(r"uploads/[\w.-]+", text, re.IGNORECASE)
            if up:
                updates.source_path = up.group(0).replace("\\", "/")

        transforms = extract_transforms(text, lower)
        if transforms:
            updates.transform = transforms

        return current.merge(updates)

    @staticmethod
    def _looks_like_path_only(text: str) -> bool:
        return (
            "/" in text
            or "\\" in text
            or text.endswith(".csv")
            or text.endswith(".json")
            or text.endswith(".ndjson")
            or text.endswith(".jsonl")
            or text.startswith("http")
            or (len(text.split()) == 1 and re.match(r"^[\w]+$", text))
        )
