from fastapi.testclient import TestClient
from src.main import app

def test_search_literal():
    client = TestClient(app)
    payload = {"q": "amor", "top_k": 3}
    response = client.post("/api/v1/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) <= 3
    if data["results"]:
        assert "id" in data["results"][0]
        assert "score" in data["results"][0]
        assert "snippet" in data["results"][0]
        assert "metadata" in data["results"][0]

def test_search_semantic():
    client = TestClient(app)
    payload = {"q": "amor", "top_k": 3, "mode": "semantic"}
    response = client.post("/api/v1/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) <= 3
    if data["results"]:
        assert "id" in data["results"][0]
        assert "score" in data["results"][0]
        assert "snippet" in data["results"][0]
        assert "metadata" in data["results"][0]
