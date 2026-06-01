import sqlite3


def test_e2e_csv_sqlite_flow(client, tmp_path, monkeypatch):
    db = tmp_path / "e2e.db"
    monkeypatch.setattr(
        "smart_ingestion.agents.csv_to_sqlite.DEFAULT_SQLITE_PATH",
        db,
    )

    r1 = client.post(
        "/api/chat",
        json={"message": "Load test_data/customers.csv into SQLite table customers"},
    )
    assert r1.status_code == 200
    data1 = r1.json()
    session_id = data1["session_id"]
    assert data1["response_type"] == "plan"

    r2 = client.post(
        "/api/confirm",
        json={"session_id": session_id, "confirmed": True},
    )
    data2 = r2.json()
    assert data2["response_type"] == "result"
    assert data2["result"]["success"] is True

    conn = sqlite3.connect(db)
    count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    conn.close()
    assert count == 5


def test_e2e_cancel_no_side_effects(client, tmp_path, monkeypatch):
    db = tmp_path / "cancel.db"
    monkeypatch.setattr(
        "smart_ingestion.agents.csv_to_sqlite.DEFAULT_SQLITE_PATH",
        db,
    )

    r1 = client.post(
        "/api/chat",
        json={"message": "Load test_data/customers.csv into SQLite table customers"},
    )
    session_id = r1.json()["session_id"]

    client.post("/api/confirm", json={"session_id": session_id, "confirmed": False})

    assert not db.exists()


def test_health_and_agents(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert "llm_provider" in health
    agents = client.get("/api/agents").json()
    ids = {a["agent_id"] for a in agents}
    assert "csv_to_sqlite" in ids
    assert "json_to_sqlite" in ids
    assert "csv_to_postgresql" in ids
    assert "csv_to_s3" in ids
    assert "s3_to_sqlite" in ids
    assert "stream_json_to_parquet" in ids
    assert "stream_json_to_json" in ids
