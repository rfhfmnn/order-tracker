from fastapi.testclient import TestClient
from app import main


def test_order_lookup_telemetry(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB_PATH", tmp_path / "orders.db")
    with TestClient(main.app) as client:
        # Existing order lookup
        response = client.get("/api/orders/standard-1001")
        assert response.status_code == 200
        assert response.json()["id"] == "standard-1001"

        # Missing order lookup
        missing_resp = client.get("/api/orders/non-existent-order")
        assert missing_resp.status_code == 404


def test_telemetry_helpers():
    from app.telemetry import flush_telemetry, init_telemetry

    init_telemetry()
    flush_telemetry()

