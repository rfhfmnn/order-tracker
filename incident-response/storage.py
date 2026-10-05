import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger("incident-response.storage")


def generate_incident_id(alert_name: str = "alert") -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    clean_name = "".join(c if c.isalnum() else "_" for c in alert_name.lower())[:24].strip("_")
    short_uid = uuid4().hex[:6]
    return f"incident_{now_str}_{clean_name}_{short_uid}"


def generate_markdown_report(incident: Dict[str, Any]) -> str:
    """Generate human and agent readable incident investigation report in Markdown."""
    inc_id = incident.get("incident_id", "Unknown")
    ts = incident.get("timestamp", "")
    alert = incident.get("alert", {})
    endpoint = incident.get("affected_endpoint", "Unknown")
    alert_name = alert.get("name", "Alert")
    status = alert.get("status", "firing")
    severity = alert.get("severity", "unknown")
    desc = alert.get("description", "")
    dashboard_link = alert.get("dashboard_link", "")

    evidence = incident.get("evidence", {})
    error_logs = evidence.get("error_logs", [])
    logs = evidence.get("logs", [])
    traces = evidence.get("traces", [])

    lines = [
        f"# Incident Report: {inc_id}",
        "",
        "## Summary",
        f"- **Alert Name**: `{alert_name}`",
        f"- **Status**: `{status.upper()}`",
        f"- **Severity**: `{severity}`",
        f"- **Affected Endpoint**: `{endpoint}`",
        f"- **Timestamp**: `{ts}`",
    ]
    if desc:
        lines.append(f"- **Description**: {desc}")
    if dashboard_link:
        lines.append(f"- **Dashboard**: [{dashboard_link}]({dashboard_link})")

    lines.extend([
        "",
        "---",
        "",
        "## Root Cause & Diagnostics",
    ])

    # Extract exceptions from logs
    exceptions = [l["exception"] for l in logs if "exception" in l and l["exception"]]
    if exceptions:
        lines.append("### Detected Exceptions in Logs")
        for exc in exceptions[:5]:
            lines.append(f"- **Exception Type**: `{exc.get('type')}`")
            lines.append(f"- **Message**: `{exc.get('message')}`")
            if exc.get("stacktrace"):
                lines.append("```python")
                lines.append(exc.get("stacktrace").strip())
                lines.append("```")
    else:
        lines.append("No explicit exception stack traces found in captured logs.")

    lines.extend([
        "",
        "---",
        "",
        f"## Distributed Traces ({len(traces)} captured)",
    ])

    if traces:
        for trace in traces:
            trace_id = trace.get("trace_id", "")
            has_errors = trace.get("has_errors", False)
            spans = trace.get("spans", [])
            lines.append(f"### Trace `{trace_id}` {'⚠️ [ERROR]' if has_errors else '✅ [OK]'}")
            lines.append(f"- Total Spans: {len(spans)}")
            lines.append("")
            lines.append("| Span Name | Duration (ms) | Status Code | Route | Error |")
            lines.append("|---|---|---|---|---|")
            for span in spans:
                s_name = span.get("name", "")
                s_dur = span.get("duration_ms", "-")
                s_attrs = span.get("attributes", {})
                s_code = s_attrs.get("http.status_code") or s_attrs.get("status_code", "-")
                s_route = s_attrs.get("http.route") or s_attrs.get("route", "-")
                s_err = span.get("status", {}).get("message") or ("Yes" if str(s_code).startswith("5") else "No")
                lines.append(f"| `{s_name}` | {s_dur} | `{s_code}` | `{s_route}` | {s_err} |")
            lines.append("")
    else:
        lines.append("No distributed traces captured for this incident.")

    lines.extend([
        "",
        "---",
        "",
        f"## Application Logs ({len(logs)} total, {len(error_logs)} errors/warnings)",
    ])

    if logs:
        lines.append("| Timestamp | Level | Message | Source | Trace ID |")
        lines.append("|---|---|---|---|---|")
        for log in logs[-25:]:  # Show recent up to 25 logs
            l_ts = log.get("timestamp", "")[:19]
            l_lvl = log.get("level", "INFO")
            l_msg = log.get("message", "").replace("\n", " ").replace("|", "/")
            l_src = ""
            if "source" in log and log["source"]:
                src = log["source"]
                l_src = f"{Path(src.get('file', '')).name}:{src.get('line', '')}"
            l_tr = log.get("trace_id", "")
            l_tr_short = l_tr[:8] + "..." if l_tr else "-"
            lines.append(f"| {l_ts} | `{l_lvl}` | {l_msg[:120]} | `{l_src}` | `{l_tr_short}` |")
    else:
        lines.append("No application logs captured for this incident.")

    lines.append("")
    return "\n".join(lines)


def save_incident(
    incidents_dir: Path,
    alert_info: Dict[str, Any],
    evidence: Dict[str, Any],
) -> Dict[str, Any]:
    """Save incident JSON, Markdown report, and update index."""
    incidents_dir.mkdir(parents=True, exist_ok=True)

    alert_name = alert_info.get("name") or "5xx_error_alert"
    incident_id = generate_incident_id(alert_name)
    now_iso = datetime.now(timezone.utc).isoformat()

    incident_record = {
        "incident_id": incident_id,
        "timestamp": now_iso,
        "affected_endpoint": alert_info.get("endpoint") or evidence.get("affected_endpoint") or "unknown",
        "alert": alert_info,
        "evidence": evidence,
    }

    # 1. Save JSON
    json_path = incidents_dir / f"{incident_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(incident_record, f, indent=2)

    # 2. Save Markdown report
    md_content = generate_markdown_report(incident_record)
    md_path = incidents_dir / f"{incident_id}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # 3. Update index.json
    index_path = incidents_dir / "index.json"
    incidents_index: List[Dict[str, Any]] = []
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                incidents_index = json.load(f)
        except Exception:
            incidents_index = []

    summary_entry = {
        "incident_id": incident_id,
        "timestamp": now_iso,
        "alert_name": alert_name,
        "status": alert_info.get("status", "firing"),
        "severity": alert_info.get("severity", "unknown"),
        "affected_endpoint": incident_record["affected_endpoint"],
        "total_logs": evidence.get("total_logs", 0),
        "error_logs_count": evidence.get("error_logs_count", 0),
        "total_traces": evidence.get("total_traces", 0),
        "json_file": str(json_path.name),
        "report_file": str(md_path.name),
    }
    # Prepend newest incident
    incidents_index.insert(0, summary_entry)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(incidents_index, f, indent=2)

    return {
        "incident_id": incident_id,
        "status": "saved",
        "affected_endpoint": incident_record["affected_endpoint"],
        "json_path": str(json_path),
        "report_path": str(md_path),
        "summary": summary_entry,
    }


def list_incidents(incidents_dir: Path) -> List[Dict[str, Any]]:
    """List all incidents from index.json or scan directory."""
    index_path = incidents_dir / "index.json"
    if index_path.exists():
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Fallback to directory scan
    incidents = []
    if incidents_dir.exists():
        for p in sorted(incidents_dir.glob("incident_*.json"), reverse=True):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    incidents.append({
                        "incident_id": data.get("incident_id", p.stem),
                        "timestamp": data.get("timestamp", ""),
                        "affected_endpoint": data.get("affected_endpoint", "unknown"),
                        "json_file": p.name,
                    })
            except Exception:
                continue
    return incidents


def get_incident(incidents_dir: Path, incident_id: str) -> Optional[Dict[str, Any]]:
    """Get single incident JSON data."""
    json_path = incidents_dir / f"{incident_id}.json"
    if not json_path.exists():
        return None
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_incident_report(incidents_dir: Path, incident_id: str) -> Optional[str]:
    """Get single incident Markdown report."""
    md_path = incidents_dir / f"{incident_id}.md"
    if not md_path.exists():
        return None
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()
