# Order Tracker

A small order tracking app for the AI Dev Tools Zoomcamp observability homework. It includes a web page, API, tests, and a Docker Compose setup. You add telemetry, alerts, and an incident responder in Homework 4.

The main user flow is creating an order and checking its status. Three sample orders are created on first startup.

## Run it

You need Docker with Compose. To run the tests, you also need Python 3.11+ and `uv`.

```bash
docker compose up --build -d --wait
```

Open <http://127.0.0.1:8000>. The API is at `/api/orders`, and the health check is at `/healthz`. Data is stored in a Docker volume and survives container recreation.

If port 8000 is occupied, set `ORDER_TRACKER_PORT`, for example:

```bash
ORDER_TRACKER_PORT=18080 docker compose up --build -d --wait
```

Run tests with `uv run --frozen pytest -q`. Stop the app with `docker compose down`. Add `-v` only if you also want to delete the order data.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Web page |
| GET | `/healthz` | Database health check |
| GET | `/api/orders` | List orders |
| POST | `/api/orders` | Create an order |
| GET | `/api/orders/{id}` | Check an order |
| PATCH | `/api/orders/{id}` | Change an order status |

The app uses SQLite to keep setup small. Run one app container at a time. The course exercise is about detecting and handling an incident, not scaling the database.

## Observability Stack

The Docker Compose setup includes a complete OpenTelemetry-native observability stack:

| Service | Port | Description |
| --- | --- | --- |
| **App** | `8000` | Order Tracker service emitting OTLP traces, metrics, and logs |
| **OpenTelemetry Collector** | `4317` (gRPC), `4318` (HTTP), `8889` (Prometheus) | Ingests OTLP telemetry from the app and routes to backend stores |
| **Prometheus** | `9090` | Scrapes and stores application metrics from the Collector |
| **Loki** | `3100` | Ingests and indexes structured application logs |
| **Tempo** | `3200` | Distributed tracing backend storing trace spans |
| **Grafana** | `3000` | Visualizes metrics, logs, and traces with pre-provisioned dashboard |
| **Incident Response** | `8001` | Receives alerts from Grafana at `POST /alerts`, captures endpoint, logs, and traces |

### Grafana Dashboard

Grafana is available at <http://localhost:3000> (default credentials: `admin` / `admin`, anonymous access is also enabled).

The **"Order Tracker - Requests & Errors"** dashboard is pre-provisioned and includes:
- **Total HTTP Requests** (Stat & rate over time)
- **Total Errors (4xx & 5xx)** (Stat counter with alerts)
- **Error Rate (%)** (Stat gauge & timeseries)
- **Order Lookup Requests** (Stat & rate by status code)
- **HTTP Request Rate by Route** (Timeseries)
- **HTTP Requests by Status Code** (Timeseries / stacked bars)
- **Error & Warning Logs** (Real-time logs from Loki)
- **All Application Logs** (Real-time logs from Loki)
- Direct cross-linking between logs and distributed traces via Tempo.

