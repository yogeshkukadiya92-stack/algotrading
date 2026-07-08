from fastapi.testclient import TestClient

from app.main import create_app


def test_app_starts_in_test_mode_without_database_connection(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@127.0.0.1:65535/tradepilot_test")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:65535/0")
    monkeypatch.setenv("JWT_SECRET", "test-secret")

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

