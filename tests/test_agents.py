import sqlite3
from pathlib import Path

import pytest

from smart_ingestion.agents.csv_to_csv import CsvToCsvAgent
from smart_ingestion.agents.csv_to_sqlite import CsvToSqliteAgent
from smart_ingestion.agents.json_to_sqlite import JsonToSqliteAgent
from smart_ingestion.config import OUTPUT_DIR
from smart_ingestion.models import DestType, IngestionIntent, SourceType


@pytest.fixture
def output_db(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setattr(
        "smart_ingestion.agents.csv_to_sqlite.DEFAULT_SQLITE_PATH",
        db,
    )
    monkeypatch.setattr(
        "smart_ingestion.agents.json_to_sqlite.DEFAULT_SQLITE_PATH",
        db,
    )
    return db


def test_csv_to_sqlite_loads_rows(output_db):
    agent = CsvToSqliteAgent()
    intent = IngestionIntent(
        source_type=SourceType.CSV,
        dest_type=DestType.SQLITE,
        source_path="test_data/customers.csv",
        table_name="customers",
        dest_path=str(output_db),
    )
    assert agent.missing_fields(intent) == []
    result = agent.execute(intent)
    assert result.success
    assert result.rows_processed == 5

    conn = sqlite3.connect(output_db)
    count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    conn.close()
    assert count == 5


def test_json_to_sqlite_loads_rows(output_db):
    agent = JsonToSqliteAgent()
    intent = IngestionIntent(
        source_type=SourceType.JSON,
        dest_type=DestType.SQLITE,
        source_path="test_data/products.json",
        table_name="products",
        dest_path=str(output_db),
    )
    result = agent.execute(intent)
    assert result.success
    assert result.rows_processed == 4


def test_csv_to_csv_transform():
    dest = OUTPUT_DIR / "customers_filtered_test.csv"
    agent = CsvToCsvAgent()
    intent = IngestionIntent(
        source_path="test_data/customers.csv",
        dest_path="data/output/customers_filtered_test.csv",
        options={"columns": ["customer_id", "name", "email"]},
    )
    result = agent.execute(intent)
    assert result.success
    content = dest.read_text(encoding="utf-8")
    assert "customer_id,name,email" in content
    assert "city" not in content.split("\n")[0]


def test_csv_agent_validation():
    agent = CsvToSqliteAgent()
    intent = IngestionIntent()
    assert "source_path" in agent.missing_fields(intent)
