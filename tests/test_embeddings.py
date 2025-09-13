from fastapi.testclient import TestClient
from src.main import app

def test_upsert_embeddings():
    client = TestClient(app)
    payload = {
        "items": [
            {"id": "AT-juan-01-001", "text": "Texto de embedding de prueba", "metadata": {"libro": "Juan"}},
            {"id": "AT-mateo-01-002", "text": "Otro texto", "metadata": {"libro": "Mateo"}}
        ],
        "namespace": "test"
    }
    response = client.post("/api/v1/embeddings/upsert", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "upserted" in data
    assert "failed" in data
    assert isinstance(data["upserted"], int)
    assert isinstance(data["failed"], list)
