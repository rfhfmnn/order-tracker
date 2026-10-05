# Incident Response Service

A dedicated service that receives alerts from Grafana at `POST /alerts` on port 8001, extracts incident diagnostic information (affected endpoint, logs from Loki, and traces from Tempo), and saves full diagnostic records to disk for incident analysis and AI agent investigation.

## Features

- **Receives Grafana Webhooks**: Listens at `POST /alerts` on port 8001 for firing alerts.
- **Affected Endpoint Identification**: Automatically detects the affected API endpoint from alert labels (`route`) and annotations (`endpoint`).
- **Telemetry Evidence Gathering**:
  - Queries **Loki** (`/loki/api/v1/query_range`) for recent logs and extracted error stack traces (`ValueError`, etc.).
  - Discovers associated `trace_id`s from log records and OpenTelemetry spans.
  - Queries **Tempo** (`/api/traces/{trace_id}`) to inspect span trees, status codes (`500`), execution durations, and span attributes.
- **Incident Persistence**:
  - Saves full structured JSON dossiers to `incident-response/incidents/<incident_id>.json`.
  - Generates comprehensive human/agent-readable Markdown reports to `incident-response/incidents/<incident_id>.md`.
  - Maintains an incident index in `incident-response/incidents/index.json`.
- **Incident Inspection APIs**:
  - `GET /healthz`: Service health check.
  - `GET /alerts`: View history of received alert payloads.
  - `GET /incidents`: List all saved incidents with summary statistics.
  - `GET /incidents/{incident_id}`: Retrieve JSON incident diagnostic package.
  - `GET /incidents/{incident_id}/report`: View formatted Markdown incident report.

## Running the Service

### 1. In Docker Compose (Integrated with Observability Stack)

The service is pre-configured in `compose.yaml`:

```bash
docker compose up --build -d incident-response
```

### 2. Standalone Local Execution

You can also run the service directly on the host using Python / uv:

```bash
uv run uvicorn incident-response.main:app --host 0.0.0.0 --port 8001
# or
python incident-response/main.py
```

Environment variables:
- `PORT`: Port to listen on (default `8001`).
- `HOST`: Host to bind (default `0.0.0.0`).
- `LOKI_URL`: Loki base URL (default `http://localhost:3100`, auto-fallback to `http://loki:3100`).
- `TEMPO_URL`: Tempo base URL (default `http://localhost:3200`, auto-fallback to `http://tempo:3200`).
- `INCIDENTS_DIR`: Directory where incident reports are saved (default `incident-response/incidents`).

## Grafana Webhook Integration

Grafana alerting is configured via `observability/grafana/provisioning/alerting/contactpoints.yaml` to route firing alerts from the "Order Tracker Alerts" group to:

```text
http://incident-response:8001/alerts
```
