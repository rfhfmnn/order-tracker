import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure incident-response directory is in python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import subprocess
from agent import run_agent_investigation
from collector import collect_evidence
from storage import get_incident, get_incident_report, list_incidents, save_incident
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("incident-response")

app = FastAPI(
    title="Incident Response Service",
    description="Receives alerts from Grafana and captures diagnostic evidence (endpoint, logs, traces)",
    version="0.1.0",
)

INCIDENTS_DIR = Path(os.getenv("INCIDENTS_DIR", current_dir / "incidents"))
received_alerts_history: List[Dict[str, Any]] = []


def extract_alert_details(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key alert metadata from Grafana webhook payload."""
    alerts = payload.get("alerts", [])
    common_labels = payload.get("commonLabels", {})
    common_annotations = payload.get("commonAnnotations", {})

    first_alert = alerts[0] if alerts and isinstance(alerts, list) else {}
    labels = first_alert.get("labels", {})
    annotations = first_alert.get("annotations", {})

    # Affected endpoint: look across labels and annotations
    endpoint = (
        labels.get("route")
        or annotations.get("endpoint")
        or labels.get("endpoint")
        or common_labels.get("route")
        or common_annotations.get("endpoint")
        or payload.get("route")
        or "unknown"
    )

    alert_name = (
        labels.get("alertname")
        or common_labels.get("alertname")
        or payload.get("title")
        or "HTTP 5xx Error Alert"
    )

    severity = (
        labels.get("severity")
        or common_labels.get("severity")
        or "critical"
    )

    status = (
        first_alert.get("status")
        or payload.get("status")
        or payload.get("state")
        or "firing"
    )

    time_window = (
        annotations.get("time_window")
        or common_annotations.get("time_window")
        or "5m"
    )

    dashboard_link = (
        annotations.get("dashboard_link")
        or common_annotations.get("dashboard_link")
        or ""
    )

    description = (
        annotations.get("description")
        or common_annotations.get("description")
        or payload.get("message")
        or ""
    )

    summary = (
        annotations.get("summary")
        or common_annotations.get("summary")
        or ""
    )

    starts_at = first_alert.get("startsAt") or datetime.now(timezone.utc).isoformat()

    return {
        "name": alert_name,
        "endpoint": endpoint,
        "status": status,
        "severity": severity,
        "time_window": time_window,
        "dashboard_link": dashboard_link,
        "description": description,
        "summary": summary,
        "starts_at": starts_at,
        "raw_payload": payload,
    }


@app.get("/")
def root():
    return {
        "service": "incident-response",
        "status": "running",
        "port": 8001,
        "endpoints": {
            "alerts": "POST /alerts",
            "health": "GET /healthz",
            "incidents": "GET /incidents",
            "incident_detail": "GET /incidents/{incident_id}",
            "incident_report": "GET /incidents/{incident_id}/report",
        },
    }


@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "incident-response"}


@app.post("/alerts", status_code=201)
async def receive_alert(request: Request):
    """
    Receives alerts from Grafana at POST /alerts.
    Extracts affected endpoint, queries Loki for logs, queries Tempo for traces,
    and saves the full diagnostic package to disk.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        logger.error("Failed to parse JSON body: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    logger.info("Received alert payload from %s: status=%s", request.client.host if request.client else "unknown", payload.get("status"))
    received_alerts_history.append({
        "received_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    })

    # 1. Extract alert details
    alert_info = extract_alert_details(payload)
    endpoint = alert_info["endpoint"]
    logger.info("Processing alert '%s' for affected endpoint: %s", alert_info["name"], endpoint)

    # 2. Collect evidence from Loki (logs) and Tempo (traces)
    evidence = collect_evidence(
        service_name="order-tracker",
        affected_endpoint=endpoint,
        time_window_seconds=3600,  # default 1 hour context
    )
    logger.info(
        "Collected evidence: %d logs (%d error logs), %d traces (trace IDs: %s)",
        evidence["total_logs"],
        evidence["error_logs_count"],
        evidence["total_traces"],
        evidence["discovered_trace_ids"],
    )

    # 3. Save incident data and report to disk
    save_result = save_incident(
        incidents_dir=INCIDENTS_DIR,
        alert_info=alert_info,
        evidence=evidence,
    )
    logger.info("Saved incident %s to %s", save_result["incident_id"], save_result["json_path"])

    # 4. Start coding assistant automatically in headless mode
    logger.info("Starting coding assistant automatically in headless mode for incident %s...", save_result["incident_id"])
    agent_cmd = os.getenv("AGENT_CMD")
    if agent_cmd:
        try:
            cmd = agent_cmd.format(incident_path=save_result["json_path"], incident_id=save_result["incident_id"])
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            agent_response = proc.stdout.strip() or proc.stderr.strip()
        except Exception as e:
            logger.error("Error executing AGENT_CMD: %s; falling back to internal agent", e)
            full_incident = get_incident(INCIDENTS_DIR, save_result["incident_id"]) or {}
            agent_response = run_agent_investigation(full_incident)
    else:
        full_incident = get_incident(INCIDENTS_DIR, save_result["incident_id"]) or {}
        agent_response = run_agent_investigation(full_incident)

    agent_file = INCIDENTS_DIR / f"{save_result['incident_id']}_agent_response.txt"
    agent_file.write_text(agent_response, encoding="utf-8")

    response_lines = [line.strip() for line in agent_response.strip().splitlines() if line.strip()]
    agent_last_line = response_lines[-1] if response_lines else ""
    logger.info("Coding assistant finished.\n%s", agent_response)

    return {
        "status": "incident_recorded",
        "incident_id": save_result["incident_id"],
        "affected_endpoint": endpoint,
        "logs_collected": evidence["total_logs"],
        "error_logs_collected": evidence["error_logs_count"],
        "traces_collected": evidence["total_traces"],
        "discovered_trace_ids": evidence["discovered_trace_ids"],
        "json_path": save_result["json_path"],
        "report_path": save_result["report_path"],
        "agent_response_path": str(agent_file),
        "agent_response": agent_response,
        "agent_last_line": agent_last_line,
    }


@app.get("/incidents/{incident_id}/agent-response", response_class=PlainTextResponse)
def get_agent_response(incident_id: str):
    """Retrieve coding assistant's response for an incident."""
    agent_file = INCIDENTS_DIR / f"{incident_id}_agent_response.txt"
    if not agent_file.exists():
        raise HTTPException(status_code=404, detail=f"Agent response for {incident_id} not found")
    return agent_file.read_text(encoding="utf-8")


@app.get("/alerts")
def get_alerts():
    """Return in-memory history of received alert payloads."""
    return received_alerts_history


@app.get("/incidents")
def get_incidents():
    """List all saved incidents."""
    return list_incidents(INCIDENTS_DIR)


@app.get("/incidents/{incident_id}")
def get_incident_detail(incident_id: str):
    """Retrieve full incident diagnostic record by ID."""
    incident = get_incident(INCIDENTS_DIR, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@app.get("/incidents/{incident_id}/report", response_class=PlainTextResponse)
def get_incident_markdown(incident_id: str):
    """Retrieve Markdown formatted incident report."""
    report = get_incident_report(INCIDENTS_DIR, incident_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} report not found")
    return report


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=False)
