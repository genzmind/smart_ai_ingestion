import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DATA_DIR = PROJECT_ROOT / "test_data"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
UPLOADS_DIR = PROJECT_ROOT / "uploads"
S3_MOCK_DIR = PROJECT_ROOT / "data" / "s3-mock"
DEFAULT_SQLITE_PATH = OUTPUT_DIR / "ingestion.db"

ALLOWED_READ_ROOTS = (TEST_DATA_DIR, OUTPUT_DIR, UPLOADS_DIR, S3_MOCK_DIR)
ALLOWED_WRITE_ROOTS = (OUTPUT_DIR, UPLOADS_DIR, S3_MOCK_DIR)

# LLM: rule_based (default) | openai
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "rule_based").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# PostgreSQL (optional; can also be set per-request in intent.database_url)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ingestion",
)

# S3: set S3_USE_LOCAL=true to use data/s3-mock/ without AWS credentials
S3_USE_LOCAL = os.getenv("S3_USE_LOCAL", "true").lower() in ("1", "true", "yes")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")  # MinIO / LocalStack

# Streaming JSON → Parquet / JSON
STREAM_BATCH_SIZE = int(os.getenv("STREAM_BATCH_SIZE", "50"))
STREAM_DEFAULT_MAX_RECORDS = os.getenv("STREAM_DEFAULT_MAX_RECORDS")  # optional cap for dev

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
S3_MOCK_DIR.mkdir(parents=True, exist_ok=True)
