from fastapi.testclient import TestClient
from src.main import app

def test_admin_reindex_real():
    client = TestClient(app)
    payload = {"batch_size": 1000}
    response = client.post("/api/v1/admin/reindex", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "accepted"


def test_admin_reindex_dry_run():
    client = TestClient(app)
    payload = {"batch_size": 500, "dry_run": True}
    response = client.post("/api/v1/admin/reindex", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "dry_run"
