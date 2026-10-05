import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("incident-response.collector")

DEFAULT_LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
DEFAULT_TEMPO_URL = os.getenv("TEMPO_URL", "http://localhost:3200")


def _try_request(urls: List[str], path: str, params: Optional[Dict[str, str]] = None, timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    """Try requesting path across candidate base URLs until one succeeds."""
    query_str = f"?{urllib.parse.urlencode(params)}" if params else ""
    for base_url in urls:
        base = base_url.rstrip("/")
        full_url = f"{base}{path}{query_str}"
        try:
            req = urllib.request.Request(full_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.debug("Failed requesting %s: %s", full_url, e)
            continue
    return None


def fetch_loki_logs(
    base_urls: Optional[List[str]] = None,
    service_name: str = "order-tracker",
    time_window_seconds: int = 3600,  # default 1 hour
    limit: int = 100,
) -> Tuple[List[Dict[str, Any]], Set[str]]:
    """
    Query Loki for recent logs from service_name.
    Returns:
        (logs_list, trace_ids_set)
    """
    if base_urls is None:
        configured = os.getenv("LOKI_URL", DEFAULT_LOKI_URL)
        # Try configured first, then fallbacks for both container & host
        base_urls = [configured, "http://localhost:3100", "http://loki:3100", "http://127.0.0.1:3100"]
        # Deduplicate while preserving order
        base_urls = list(dict.fromkeys(base_urls))

    now_ns = int(time.time() * 1e9)
    start_ns = now_ns - int(time_window_seconds * 1e9)

    params = {
        "query": f'{{service_name="{service_name}"}}',
        "start": str(start_ns),
        "end": str(now_ns),
        "limit": str(limit),
        "direction": "BACKWARD",
    }

    data = _try_request(base_urls, "/loki/api/v1/query_range", params=params)
    parsed_logs: List[Dict[str, Any]] = []
    trace_ids: Set[str] = set()

    streams = data.get("data", {}).get("result", []) if data and data.get("status") == "success" else []

    # If no logs in explicit time window, fallback to querying most recent without start restriction
    if not streams:
        fallback_params = {
            "query": f'{{service_name="{service_name}"}}',
            "limit": str(limit),
            "direction": "BACKWARD",
        }
        data = _try_request(base_urls, "/loki/api/v1/query_range", params=fallback_params)
        streams = data.get("data", {}).get("result", []) if data and data.get("status") == "success" else []
    for stream_obj in streams:
        stream_labels = stream_obj.get("stream", {})
        values = stream_obj.get("values", [])

        stream_trace_id = stream_labels.get("trace_id")
        if stream_trace_id:
            # Handle possible hex prefixes like 0x
            stream_trace_id = stream_trace_id.removeprefix("0x")
            trace_ids.add(stream_trace_id)

        stream_span_id = stream_labels.get("span_id", "")
        level = stream_labels.get("level") or stream_labels.get("severity_text") or "UNKNOWN"
        exc_type = stream_labels.get("exception_type")
        exc_msg = stream_labels.get("exception_message")
        exc_trace = stream_labels.get("exception_stacktrace")
        file_path = stream_labels.get("code_file_path")
        func_name = stream_labels.get("code_function_name")
        line_num = stream_labels.get("code_line_number")

        for val in values:
            if not isinstance(val, (list, tuple)) or len(val) < 2:
                continue
            ts_ns_str, message = val[0], val[1]
            try:
                ts_sec = float(ts_ns_str) / 1e9
                ts_iso = datetime.fromtimestamp(ts_sec, tz=timezone.utc).isoformat()
            except Exception:
                ts_iso = str(ts_ns_str)

            # Check if log message itself contains trace_id
            if "trace_id" in message and not stream_trace_id:
                try:
                    import re
                    match = re.search(r'["\']?trace_id["\']?:\s*["\']?(0x[a-f0-9]+|[a-f0-9]{16,32})["\']?', message)
                    if match:
                        t_id = match.group(1).removeprefix("0x")
                        trace_ids.add(t_id)
                except Exception:
                    pass

            entry: Dict[str, Any] = {
                "timestamp": ts_iso,
                "timestamp_ns": ts_ns_str,
                "level": level.upper(),
                "message": message,
                "trace_id": stream_trace_id or None,
                "span_id": stream_span_id or None,
                "service": service_name,
            }
            if exc_type or exc_msg or exc_trace:
                entry["exception"] = {
                    "type": exc_type,
                    "message": exc_msg,
                    "stacktrace": exc_trace,
                }
            if file_path or func_name:
                entry["source"] = {
                    "file": file_path,
                    "function": func_name,
                    "line": line_num,
                }
            parsed_logs.append(entry)

    # Sort logs by timestamp ascending
    parsed_logs.sort(key=lambda x: x.get("timestamp_ns", ""))
    return parsed_logs, trace_ids


def fetch_tempo_trace(base_urls: Optional[List[str]], trace_id: str) -> Optional[Dict[str, Any]]:
    """Fetch trace details from Tempo given a trace ID."""
    if not trace_id:
        return None

    clean_trace_id = trace_id.removeprefix("0x").strip()
    if base_urls is None:
        configured = os.getenv("TEMPO_URL", DEFAULT_TEMPO_URL)
        base_urls = [configured, "http://localhost:3200", "http://tempo:3200", "http://127.0.0.1:3200"]
        base_urls = list(dict.fromkeys(base_urls))

    data = _try_request(base_urls, f"/api/traces/{clean_trace_id}")
    if not data:
        return None

    # Parse OTLP batches
    spans: List[Dict[str, Any]] = []
    root_service = "order-tracker"
    batches = data.get("batches", [])

    for batch in batches:
        resource = batch.get("resource", {})
        res_attrs = {
            attr.get("key"): (attr.get("value", {}).get("stringValue") or attr.get("value", {}).get("intValue"))
            for attr in resource.get("attributes", [])
        }
        batch_service = res_attrs.get("service.name", root_service)

        for scope_span in batch.get("scopeSpans", []):
            scope = scope_span.get("scope", {}).get("name", "")
            for s in scope_span.get("spans", []):
                span_name = s.get("name")
                span_id = s.get("spanId")
                parent_id = s.get("parentSpanId")
                start_nano = s.get("startTimeUnixNano")
                end_nano = s.get("endTimeUnixNano")
                status = s.get("status", {})

                # Compute duration in milliseconds
                duration_ms = None
                if start_nano and end_nano:
                    try:
                        duration_ms = round((int(end_nano) - int(start_nano)) / 1e6, 2)
                    except Exception:
                        pass

                # Parse span attributes
                raw_attrs = s.get("attributes", [])
                span_attrs: Dict[str, Any] = {}
                for attr in raw_attrs:
                    k = attr.get("key")
                    v_obj = attr.get("value", {})
                    val = (
                        v_obj.get("stringValue")
                        if "stringValue" in v_obj
                        else v_obj.get("intValue")
                        if "intValue" in v_obj
                        else v_obj.get("boolValue")
                        if "boolValue" in v_obj
                        else v_obj.get("doubleValue")
                    )
                    span_attrs[k] = val

                # Parse span events (e.g. exceptions)
                events: List[Dict[str, Any]] = []
                for ev in s.get("events", []):
                    ev_name = ev.get("name")
                    ev_attrs = {
                        a.get("key"): (a.get("value", {}).get("stringValue") or a.get("value", {}).get("intValue"))
                        for a in ev.get("attributes", [])
                    }
                    events.append({"name": ev_name, "attributes": ev_attrs})

                spans.append({
                    "span_id": span_id,
                    "parent_span_id": parent_id,
                    "name": span_name,
                    "scope": scope,
                    "service": batch_service,
                    "duration_ms": duration_ms,
                    "status": {
                        "code": status.get("code"),
                        "message": status.get("message"),
                    },
                    "attributes": span_attrs,
                    "events": events,
                })

    return {
        "trace_id": clean_trace_id,
        "spans_count": len(spans),
        "spans": spans,
        "has_errors": any(
            s.get("status", {}).get("code") in ("STATUS_CODE_ERROR", 2, "2", "ERROR")
            or str(s.get("attributes", {}).get("status_code", "")).startswith("5")
            for s in spans
        ),
    }


def search_tempo_traces(
    base_urls: Optional[List[str]] = None,
    service_name: str = "order-tracker",
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Search Tempo for recent traces matching service_name."""
    if base_urls is None:
        configured = os.getenv("TEMPO_URL", DEFAULT_TEMPO_URL)
        base_urls = [configured, "http://localhost:3200", "http://tempo:3200", "http://127.0.0.1:3200"]
        base_urls = list(dict.fromkeys(base_urls))

    params = {
        "tags": f"service.name={service_name}",
        "limit": str(limit),
    }

    data = _try_request(base_urls, "/api/search", params=params)
    if not data:
        return []

    return data.get("traces", [])


def collect_evidence(
    service_name: str = "order-tracker",
    affected_endpoint: Optional[str] = None,
    time_window_seconds: int = 900,
) -> Dict[str, Any]:
    """
    Gathers logs and traces relevant to an alert.
    Returns aggregated evidence dictionary.
    """
    # 1. Fetch logs from Loki
    logs, discovered_trace_ids = fetch_loki_logs(
        service_name=service_name,
        time_window_seconds=time_window_seconds,
        limit=100,
    )

    # 2. Search Tempo for recent traces
    search_results = search_tempo_traces(service_name=service_name, limit=10)
    for t in search_results:
        t_id = t.get("traceID")
        if t_id:
            discovered_trace_ids.add(t_id.removeprefix("0x"))

    # 3. Fetch detailed spans for all discovered trace IDs
    traces_details: List[Dict[str, Any]] = []
    for trace_id in discovered_trace_ids:
        t_detail = fetch_tempo_trace(None, trace_id)
        if t_detail:
            traces_details.append(t_detail)

    # Filter/rank logs: count error logs
    error_logs = [l for l in logs if l.get("level") in ("ERROR", "CRITICAL", "WARN") or "exception" in l]

    return {
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "service_name": service_name,
        "affected_endpoint": affected_endpoint,
        "time_window_seconds": time_window_seconds,
        "total_logs": len(logs),
        "error_logs_count": len(error_logs),
        "logs": logs,
        "error_logs": error_logs,
        "total_traces": len(traces_details),
        "traces": traces_details,
        "discovered_trace_ids": list(discovered_trace_ids),
    }
