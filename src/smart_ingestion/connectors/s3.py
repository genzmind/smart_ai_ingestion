import shutil
from pathlib import Path

from smart_ingestion.config import AWS_REGION, S3_ENDPOINT_URL, S3_MOCK_DIR, S3_USE_LOCAL


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Parse s3://bucket/key or bucket/key into (bucket, key)."""
    text = uri.strip()
    if text.startswith("s3://"):
        text = text[5:]
    parts = text.split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid S3 URI: {uri}")
    return parts[0], parts[1]


class S3Storage:
    """AWS S3 or local mock storage under data/s3-mock/."""

    def __init__(self) -> None:
        self._use_local = S3_USE_LOCAL

    def upload_file(self, local_path: Path, bucket: str, key: str) -> str:
        if self._use_local:
            dest = S3_MOCK_DIR / bucket / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest)
            return f"s3://{bucket}/{key} (local: {dest})"

        import boto3

        client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            endpoint_url=S3_ENDPOINT_URL or None,
        )
        client.upload_file(str(local_path), bucket, key)
        return f"s3://{bucket}/{key}"

    def download_file(self, bucket: str, key: str, local_path: Path) -> Path:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if self._use_local:
            source = S3_MOCK_DIR / bucket / key
            if not source.exists():
                raise FileNotFoundError(f"S3 object not found (local mock): {source}")
            shutil.copy2(source, local_path)
            return local_path

        import boto3

        client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            endpoint_url=S3_ENDPOINT_URL or None,
        )
        client.download_file(bucket, key, str(local_path))
        return local_path


s3_storage = S3Storage()
