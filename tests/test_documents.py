from fastapi.testclient import TestClient
from src.main import app

def test_get_document_by_id():
    client = TestClient(app)
    # Usar un id conocido del corpus, por ejemplo '1' (ajustar según corpus real)
    response = client.get("/api/v1/documents/1")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "id" in data
        assert "text" in data
        assert "metadata" in data
        assert "created_at" in data
        assert "updated_at" in data


def test_list_documents():
    client = TestClient(app)
    response = client.get("/api/v1/documents?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert isinstance(data["items"], list)
    assert data["limit"] == 5
    assert data["offset"] == 0
    if data["items"]:
        doc = data["items"][0]
        assert "id" in doc
        assert "text" in doc
        assert "metadata" in doc
        assert "created_at" in doc
        assert "updated_at" in doc


def test_post_document():
    client = TestClient(app)
    payload = {
        "id": "AT-genesis-01-001",
        "text": "Texto de prueba",
        "metadata": {"libro": "Génesis"}
    }
    response = client.post("/api/v1/documents", json=payload)
    assert response.status_code in (200, 201)
    if response.status_code in (200, 201):
        data = response.json()
        assert "id" in data
        assert data["status"] in ("created", "updated")
