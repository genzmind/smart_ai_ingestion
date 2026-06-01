from smart_ingestion.models import ResponseType, SessionState
from smart_ingestion.orchestrator import OrchestratorService
from smart_ingestion.session import session_store


def test_missing_table_name_prompt():
    orch = OrchestratorService()
    session_store._sessions.clear()
    r1 = orch.handle_message(None, "Load test_data/customers.csv into SQLite")
    assert r1.response_type == ResponseType.QUESTION
    assert r1.missing_field == "table_name"

    r2 = orch.handle_message(r1.session_id, "customers")
    assert r2.response_type == ResponseType.PLAN
    assert r2.plan is not None
    assert r2.plan.agent_id == "csv_to_sqlite"


def test_confirm_executes_ingestion(tmp_path, monkeypatch):
    db = tmp_path / "orch.db"
    monkeypatch.setattr(
        "smart_ingestion.agents.csv_to_sqlite.DEFAULT_SQLITE_PATH",
        db,
    )

    orch = OrchestratorService()
    session_store._sessions.clear()
    msg = "Load test_data/customers.csv into SQLite table customers"
    plan_resp = orch.handle_message(None, msg)
    assert plan_resp.response_type == ResponseType.PLAN

    cancel = orch.handle_confirm(plan_resp.session_id, False)
    assert cancel.session_state == SessionState.IDLE

    plan_resp2 = orch.handle_message(plan_resp.session_id, msg)
    result = orch.handle_confirm(plan_resp2.session_id, True)
    assert result.response_type == ResponseType.RESULT
    assert result.result is not None
    assert result.result.success
    assert result.result.rows_processed == 5
