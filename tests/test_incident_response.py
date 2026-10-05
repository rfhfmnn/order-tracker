import json
import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add incident-response to sys.path
incident_response_dir = Path(__file__).parent.parent / "incident-response"
sys.path.insert(0, str(incident_response_dir))

from main import app, extract_alert_details
import storage


@pytest.fixture
def temp_incidents_dir(tmp_path, monkeypatch):
    test_dir = tmp_path / "incidents"
    monkeypatch.setattr("main.INCIDENTS_DIR", test_dir)
    return test_dir


@pytest.fixture
def client(temp_incidents_dir):
    with TestClient(app) as test_client:
        yield test_client


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "incident-response"}


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "incident-response"
    assert response.json()["port"] == 8001


def test_extract_alert_details_grafana_unified():
    payload = {
        "receiver": "incident-response-webhook",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HTTP 5xx Error Alert",
                    "route": "/api/orders/{order_id}",
                    "severity": "critical"
                },
                "annotations": {
                    "endpoint": "/api/orders/{order_id}",
                    "summary": "5xx server errors detected on /api/orders/{order_id}",
                    "description": "Endpoint /api/orders/{order_id} returned 5xx responses",
                    "time_window": "5m",
                    "dashboard_link": "http://localhost:3000/d/order-tracker-metrics"
                },
                "startsAt": "2026-10-05T17:38:00Z"
            }
        ]
    }
    details = extract_alert_details(payload)
    assert details["name"] == "HTTP 5xx Error Alert"
    assert details["endpoint"] == "/api/orders/{order_id}"
    assert details["status"] == "firing"
    assert details["severity"] == "critical"
    assert details["time_window"] == "5m"
    assert details["dashboard_link"] == "http://localhost:3000/d/order-tracker-metrics"


def test_extract_alert_details_fallback():
    payload = {
        "status": "firing",
        "commonLabels": {
            "route": "/healthz",
            "alertname": "CustomAlert"
        }
    }
    details = extract_alert_details(payload)
    assert details["name"] == "CustomAlert"
    assert details["endpoint"] == "/healthz"


def test_receive_alert_and_save_incident(client, temp_incidents_dir, monkeypatch):
    # Mock evidence collection to test storage and response cleanly
    fake_evidence = {
        "collected_at": "2026-10-05T18:00:00Z",
        "service_name": "order-tracker",
        "affected_endpoint": "/api/orders/{order_id}",
        "time_window_seconds": 900,
        "total_logs": 2,
        "error_logs_count": 1,
        "logs": [
            {
                "timestamp": "2026-10-05T17:59:00Z",
                "level": "INFO",
                "message": "Looking up order: express-1002",
                "trace_id": "d84ff99f7961000dbac5520d6e5c5e02",
                "service": "order-tracker",
            },
            {
                "timestamp": "2026-10-05T17:59:01Z",
                "level": "ERROR",
                "message": "Error retrieving order details: day is out of range for month",
                "trace_id": "d84ff99f7961000dbac5520d6e5c5e02",
                "exception": {
                    "type": "ValueError",
                    "message": "day is out of range for month",
                    "stacktrace": "Traceback (most recent call last):\n  File 'main.py', line 67\nValueError",
                },
                "source": {"file": "main.py", "function": "get_order", "line": "179"},
                "service": "order-tracker",
            }
        ],
        "error_logs": [],
        "total_traces": 1,
        "traces": [
            {
                "trace_id": "d84ff99f7961000dbac5520d6e5c5e02",
                "spans_count": 1,
                "has_errors": True,
                "spans": [
                    {
                        "span_id": "270957e96a5ce574",
                        "name": "order_lookup",
                        "duration_ms": 12.5,
                        "status": {"code": 2, "message": "day is out of range for month"},
                        "attributes": {
                            "http.route": "/api/orders/{order_id}",
                            "http.status_code": 500,
                        },
                        "events": [],
                    }
                ],
            }
        ],
        "discovered_trace_ids": ["d84ff99f7961000dbac5520d6e5c5e02"],
    }

    monkeypatch.setattr("main.collect_evidence", lambda **kwargs: fake_evidence)

    alert_payload = {
        "receiver": "incident-response-webhook",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HTTP 5xx Error Alert",
                    "route": "/api/orders/{order_id}",
                    "severity": "critical"
                },
                "annotations": {
                    "endpoint": "/api/orders/{order_id}",
                    "summary": "5xx server errors detected on /api/orders/{order_id}",
                    "description": "Endpoint /api/orders/{order_id} returned 5xx responses",
                    "time_window": "5m",
                    "dashboard_link": "http://localhost:3000/d/order-tracker-metrics"
                }
            }
        ]
    }

    resp = client.post("/alerts", json=alert_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "incident_recorded"
    assert data["affected_endpoint"] == "/api/orders/{order_id}"
    assert data["logs_collected"] == 2
    assert data["error_logs_collected"] == 1
    assert data["traces_collected"] == 1
    assert "d84ff99f7961000dbac5520d6e5c5e02" in data["discovered_trace_ids"]

    incident_id = data["incident_id"]

    # Verify JSON file was created on disk
    json_path = Path(data["json_path"])
    assert json_path.exists()
    with open(json_path, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    assert saved_json["incident_id"] == incident_id
    assert saved_json["affected_endpoint"] == "/api/orders/{order_id}"
    assert len(saved_json["evidence"]["logs"]) == 2
    assert len(saved_json["evidence"]["traces"]) == 1

    # Verify Markdown report was created on disk
    md_path = Path(data["report_path"])
    assert md_path.exists()
    report_text = md_path.read_text(encoding="utf-8")
    assert incident_id in report_text
    assert "/api/orders/{order_id}" in report_text
    assert "ValueError" in report_text
    assert "day is out of range for month" in report_text

    # Test GET /incidents
    incidents_resp = client.get("/incidents")
    assert incidents_resp.status_code == 200
    inc_list = incidents_resp.json()
    assert len(inc_list) == 1
    assert inc_list[0]["incident_id"] == incident_id
    assert inc_list[0]["affected_endpoint"] == "/api/orders/{order_id}"

    # Test GET /incidents/{incident_id}
    detail_resp = client.get(f"/incidents/{incident_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["incident_id"] == incident_id

    # Test GET /incidents/{incident_id}/report
    report_resp = client.get(f"/incidents/{incident_id}/report")
    assert report_resp.status_code == 200
    assert "Incident Report" in report_resp.text
    assert incident_id in report_resp.text
