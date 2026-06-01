from pathlib import Path

from smart_ingestion.config import UPLOADS_DIR


def test_upload_csv(client):
    content = b"id,name\n1,Test\n"
    response = client.post(
        "/api/upload",
        files={"file": ("sample.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == "uploads/sample.csv"
    assert Path(UPLOADS_DIR / "sample.csv").exists()
