import shutil

import pytest

from smart_ingestion.agents.csv_to_s3 import CsvToS3Agent
from smart_ingestion.agents.s3_to_sqlite import S3ToSqliteAgent
from smart_ingestion.config import S3_MOCK_DIR, TEST_DATA_DIR
from smart_ingestion.connectors.s3 import s3_storage
from smart_ingestion.models import DestType, IngestionIntent, SourceType


@pytest.fixture(autouse=True)
def local_s3():
    s3_storage._use_local = True
    yield
    s3_storage._use_local = True


@pytest.fixture
def s3_seed():
    bucket = "my-bucket"
    key = "ingested/customers.csv"
    dest = S3_MOCK_DIR / bucket / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(TEST_DATA_DIR / "customers.csv", dest)
    yield bucket, key


def test_csv_to_s3_local():
    agent = CsvToS3Agent()
    intent = IngestionIntent(
        source_path="test_data/customers.csv",
        s3_bucket="test-bucket",
        s3_key="exports/customers.csv",
        source_type=SourceType.CSV,
        dest_type=DestType.S3,
    )
    result = agent.execute(intent)
    assert result.success
    assert (S3_MOCK_DIR / "test-bucket" / "exports/customers.csv").exists()


def test_s3_to_sqlite(s3_seed, tmp_path, monkeypatch):
    db = tmp_path / "from_s3.db"
    monkeypatch.setattr(
        "smart_ingestion.agents.s3_to_sqlite.DEFAULT_SQLITE_PATH",
        db,
    )
    bucket, key = s3_seed
    agent = S3ToSqliteAgent()
    intent = IngestionIntent(
        source_type=SourceType.S3,
        dest_type=DestType.SQLITE,
        s3_bucket=bucket,
        s3_key=key,
        table_name="s3_customers",
        dest_path=str(db),
    )
    result = agent.execute(intent)
    assert result.success
    assert result.rows_processed == 5
