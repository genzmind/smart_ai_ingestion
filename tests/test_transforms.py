import sqlite3

import pytest

from smart_ingestion.agents.csv_to_sqlite import CsvToSqliteAgent
from smart_ingestion.connectors.ingestion_pipeline import load_and_transform
from smart_ingestion.connectors.transforms import (
    apply_aggregate,
    apply_filter,
    apply_join,
    apply_transforms,
)
from smart_ingestion.models.transforms import (
    AggregateMetric,
    AggregateSpec,
    FilterCondition,
    FilterSpec,
    JoinSpec,
    TransformSpec,
)
from smart_ingestion.models import DestType, IngestionIntent, SourceType
from smart_ingestion.orchestrator import OrchestratorService
from smart_ingestion.session import session_store


@pytest.fixture
def writable_tmp(tmp_path, monkeypatch):
    from smart_ingestion.config import OUTPUT_DIR

    monkeypatch.setattr("smart_ingestion.utils.ALLOWED_WRITE_ROOTS", (OUTPUT_DIR, tmp_path))
    return tmp_path


def test_filter_records():
    records = [
        {"event_type": "purchase", "n": 1},
        {"event_type": "page_view", "n": 2},
    ]
    spec = FilterSpec(conditions=[FilterCondition(field="event_type", operator="eq", value="purchase")])
    out = apply_filter(records, spec)
    assert len(out) == 1
    assert out[0]["event_type"] == "purchase"


def test_aggregate_count_by_field():
    records = [
        {"event_type": "purchase"},
        {"event_type": "purchase"},
        {"event_type": "click"},
    ]
    spec = AggregateSpec(
        group_by=["event_type"],
        metrics=[AggregateMetric(field="event_type", function="count")],
    )
    out = apply_aggregate(records, spec)
    assert len(out) == 2
    counts = {r["event_type"]: r["count_event_type"] for r in out}
    assert counts["purchase"] == 2


def test_join_customers_labels():
    left = [
        {"customer_id": "1", "name": "Alice"},
        {"customer_id": "2", "name": "Bob"},
    ]
    right = [
        {"customer_id": "1", "segment": "enterprise"},
        {"customer_id": "2", "segment": "smb"},
    ]
    spec = JoinSpec(left_on="customer_id", right_on="customer_id", how="inner", right_source_path="x")
    out = apply_join(left, right, spec)
    assert len(out) == 2
    assert out[0]["segment"] == "enterprise"


def test_load_and_transform_filter(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setattr("smart_ingestion.agents.csv_to_sqlite.DEFAULT_SQLITE_PATH", db)
    intent = IngestionIntent(
        source_path="test_data/customers.csv",
        table_name="cust_filtered",
        transform=TransformSpec(
            requested=["filter"],
            filter=FilterSpec(
                conditions=[FilterCondition(field="country", operator="eq", value="USA")]
            ),
        ),
    )
    rows = load_and_transform(intent)
    assert len(rows) == 3
    agent = CsvToSqliteAgent()
    result = agent.execute(intent)
    assert result.success
    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM cust_filtered").fetchone()[0]
    conn.close()
    assert count == 3


def test_stream_filter_to_parquet(writable_tmp):
    from smart_ingestion.agents.stream_json_to_parquet import StreamJsonToParquetAgent
    import pyarrow.parquet as pq

    out = writable_tmp / "purchases.parquet"
    intent = IngestionIntent(
        source_type=SourceType.STREAM_JSON,
        dest_type=DestType.PARQUET,
        source_path="test_data/events.ndjson",
        dest_path=str(out),
        transform=TransformSpec(
            requested=["filter"],
            filter=FilterSpec(
                conditions=[FilterCondition(field="event_type", operator="eq", value="purchase")]
            ),
        ),
    )
    result = StreamJsonToParquetAgent().execute(intent)
    assert result.success
    assert result.rows_processed == 1
    assert pq.read_table(out).num_rows == 1


def test_orchestrator_asks_filter_value():
    session_store._sessions.clear()
    orch = OrchestratorService()
    resp = orch.handle_message(
        None,
        "Load test_data/customers.csv into SQLite table t where country eq USA",
    )
    assert resp.response_type.value in ("plan", "question")


@pytest.fixture
def writable_tmp(tmp_path, monkeypatch):
    from smart_ingestion.config import OUTPUT_DIR

    monkeypatch.setattr("smart_ingestion.utils.ALLOWED_WRITE_ROOTS", (OUTPUT_DIR, tmp_path))
    return tmp_path
