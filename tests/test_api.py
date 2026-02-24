from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_user_data():
    response = client.get("/api/user_data?user_id=224223270")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        data = response.json()
        assert "user_id" in data
        assert "manh_balance" in data
