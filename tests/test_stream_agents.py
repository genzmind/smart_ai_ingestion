import json

import pyarrow.parquet as pq
import pytest

from smart_ingestion.agents.stream_json_to_json import StreamJsonToJsonAgent
from smart_ingestion.agents.stream_json_to_parquet import StreamJsonToParquetAgent
from smart_ingestion.config import OUTPUT_DIR
from smart_ingestion.models import DestType, IngestionIntent, SourceType
from smart_ingestion.orchestrator import OrchestratorService
from smart_ingestion.session import session_store


@pytest.fixture
def writable_tmp(tmp_path, monkeypatch):
    roots = (OUTPUT_DIR, tmp_path)
    monkeypatch.setattr("smart_ingestion.utils.ALLOWED_WRITE_ROOTS", roots)
    return tmp_path


def test_stream_ndjson_to_parquet(writable_tmp):
    parquet_out = writable_tmp / "events.parquet"
    agent = StreamJsonToParquetAgent()
    intent = IngestionIntent(
        source_type=SourceType.STREAM_JSON,
        dest_type=DestType.PARQUET,
        source_path="test_data/events.ndjson",
        dest_path=str(parquet_out),
        options={"batch_size": 2},
    )
    result = agent.execute(intent)
    assert result.success
    assert result.rows_processed == 6
    table = pq.read_table(parquet_out)
    assert table.num_rows == 6


def test_stream_ndjson_to_json_ndjson(writable_tmp):
    out = writable_tmp / "out.ndjson"
    agent = StreamJsonToJsonAgent()
    intent = IngestionIntent(
        source_type=SourceType.STREAM_JSON,
        dest_type=DestType.JSON_FILE,
        source_path="test_data/events.ndjson",
        dest_path=str(out),
        options={"json_format": "ndjson"},
    )
    result = agent.execute(intent)
    assert result.success
    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 6
    assert json.loads(lines[0])["event_id"] == "e1"


def test_stream_ndjson_to_json_array(writable_tmp):
    out = writable_tmp / "out.json"
    agent = StreamJsonToJsonAgent()
    intent = IngestionIntent(
        source_path="test_data/events.ndjson",
        dest_path=str(out),
        options={"json_format": "json_array"},
    )
    result = agent.execute(intent)
    assert result.success
    data = json.loads(out.read_text(encoding="utf-8"))
    assert len(data) == 6


def test_orchestrator_routes_stream_parquet():
    session_store._sessions.clear()
    orch = OrchestratorService()
    resp = orch.handle_message(
        None,
        "Stream test_data/events.ndjson to Parquet at data/output/events_stream.parquet",
    )
    assert resp.response_type.value == "plan"
    assert resp.plan.agent_id == "stream_json_to_parquet"


def test_rule_based_stream_intent():
    from smart_ingestion.llm.rule_based import RuleBasedLLM

    llm = RuleBasedLLM()
    intent = llm.extract_intent(
        "Stream real-time JSON from test_data/events.ndjson to data/output/events.ndjson",
        IngestionIntent(),
    )
    assert intent.source_type == SourceType.STREAM_JSON
    assert intent.source_path == "test_data/events.ndjson"
