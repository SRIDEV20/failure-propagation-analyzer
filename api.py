import json
import os
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.analysis import find_root_causes
from engine.impact import SERVICE_WEIGHTS


AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1"
STATE_TABLE_NAME = os.getenv("STATE_TABLE_NAME", "service_state")
GRAPH_TABLE_NAME = os.getenv("GRAPH_TABLE_NAME", "service_dependency_graph")
LOG_GROUP_NAME = os.getenv("LOG_GROUP_NAME") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or "/aws/lambda/failure_propagation"
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in (os.getenv("CORS_ALLOWED_ORIGINS") or "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173").split(",")
    if origin.strip()
]
TABLE_ALIAS_CANDIDATES = {
    "state": [STATE_TABLE_NAME, "service_state", "service_state_cdk"],
    "graph": [GRAPH_TABLE_NAME, "service_dependency_graph", "service_dependency_graph_cdk"],
}

app = FastAPI(title="Failure Propagation Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
logs_client = boto3.client("logs", region_name=AWS_REGION)


def resolve_table(table_names: list[str]):
    candidates = [name for name in dict.fromkeys(name for name in table_names if name)]
    if not candidates:
        raise ValueError("No DynamoDB table names were provided")

    for table_name in candidates:
        table = dynamodb.Table(table_name)

        try:
            response = table.scan(Limit=1)
        except (BotoCoreError, ClientError) as error:
            continue

        if response.get("Items"):
            return table

    return dynamodb.Table(candidates[0])


state_table = resolve_table(TABLE_ALIAS_CANDIDATES["state"])
graph_table = resolve_table(TABLE_ALIAS_CANDIDATES["graph"])


class ServiceMetrics(BaseModel):
    latency_ms: Optional[int] = None
    error_rate: Optional[float] = None
    timeout: Optional[bool] = False


def scan_all_items(table) -> List[dict]:
    items: List[dict] = []
    scan_kwargs: Dict[str, Any] = {}

    while True:
        response = table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

        scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

    return items


def normalize_state(value: Optional[str]) -> str:
    if not value:
        return "UNKNOWN"

    state = value.strip().upper()
    if state in {"HEALTHY", "OK"}:
        return "HEALTHY"
    if state in {"DEGRADED", "WARNING"}:
        return "DEGRADED"
    if state in {"FAILED", "UNHEALTHY", "CRITICAL"}:
        return "FAILED"
    return "UNKNOWN"


def evaluate_health(metrics: dict) -> str:
    if metrics.get("timeout") is True:
        return "FAILED"

    latency = metrics.get("latency_ms")
    error_rate = metrics.get("error_rate")

    if latency is not None and latency > 1000:
        return "DEGRADED"

    if error_rate is not None and error_rate > 0.2:
        return "DEGRADED"

    return "HEALTHY"


def to_iso_timestamp(epoch_millis: Optional[int]) -> str:
    if not epoch_millis:
        return ""

    return datetime.fromtimestamp(epoch_millis / 1000, tz=timezone.utc).isoformat()


def load_dependency_graph() -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    dependency_graph: Dict[str, List[str]] = {}
    dependent_graph: Dict[str, List[str]] = defaultdict(list)

    for item in scan_all_items(graph_table):
        service = item.get("service_name")
        if not service:
            continue

        dependencies = item.get("depends_on", []) or []
        dependencies = [dependency for dependency in dependencies if isinstance(dependency, str) and dependency]
        dependency_graph[service] = dependencies

        for dependency in dependencies:
            dependent_graph[dependency].append(service)

    return dependency_graph, dependent_graph


def load_state_items() -> Dict[str, dict]:
    items: Dict[str, dict] = {}

    for item in scan_all_items(state_table):
        service = item.get("service_name")
        if service:
            items[service] = item

    return items


def build_service_set(dependency_graph: Dict[str, List[str]], state_items: Dict[str, dict]) -> List[str]:
    services = set(dependency_graph.keys())
    services.update(state_items.keys())

    for dependencies in dependency_graph.values():
        services.update(dependencies)

    return sorted(services)


def compute_levels(dependency_graph: Dict[str, List[str]]) -> Dict[str, int]:
    cache: Dict[str, int] = {}

    def get_level(service: str, trail: Optional[set[str]] = None) -> int:
        cached = cache.get(service)
        if cached is not None:
            return cached

        trail = trail or set()
        if service in trail:
            return 0

        dependencies = dependency_graph.get(service, [])
        if not dependencies:
            cache[service] = 0
            return 0

        next_trail = set(trail)
        next_trail.add(service)
        level = 1 + max(get_level(dependency, next_trail) for dependency in dependencies)
        cache[service] = level
        return level

    for service in dependency_graph:
        get_level(service)

    return cache


def propagate_states(
    dependency_graph: Dict[str, List[str]],
    dependent_graph: Dict[str, List[str]],
    local_state: Dict[str, str],
) -> Dict[str, str]:
    final_state = local_state.copy()
    queue = deque(service for service, state in final_state.items() if state in {"FAILED", "DEGRADED"})

    while queue:
        current = queue.popleft()
        for dependent in dependent_graph.get(current, []):
            if final_state.get(dependent) == "FAILED":
                continue

            if final_state.get(dependent) != "DEGRADED":
                final_state[dependent] = "DEGRADED"
                queue.append(dependent)

    for service in dependency_graph:
        final_state.setdefault(service, "UNKNOWN")

    return final_state


def detect_root_failures(dependency_graph: Dict[str, List[str]], final_state: Dict[str, str]) -> List[str]:
    return sorted(find_root_causes(dependency_graph, final_state))


def count_blast_radius(service: str, dependent_graph: Dict[str, List[str]]) -> int:
    visited = set()
    queue = deque(dependent_graph.get(service, []))

    while queue:
        dependent = queue.popleft()
        if dependent in visited:
            continue

        visited.add(dependent)
        queue.extend(dependent_graph.get(dependent, []))

    return len(visited)


def confidence_score(dependencies: List[str], is_root_cause: bool, propagated: bool, final_state: str) -> int:
    score = 92 - len(dependencies) * 4
    if is_root_cause:
        score += 8
    if propagated:
        score -= 5
    if final_state == "UNKNOWN":
        score -= 18

    return max(0, min(100, score))


def severity_for_service(service_state: str, is_root_cause: bool) -> str:
    if is_root_cause or service_state == "FAILED":
        return "critical"
    if service_state == "DEGRADED":
        return "warning"
    return "info"


def query_recent_logs(limit: int = 100) -> List[dict]:
    if not LOG_GROUP_NAME:
        return []

    start_time = int((time.time() - 24 * 3600) * 1000)

    try:
        response = logs_client.filter_log_events(
            logGroupName=LOG_GROUP_NAME,
            startTime=start_time,
            limit=limit,
            interleaved=True,
        )
    except (BotoCoreError, ClientError):
        return []

    log_entries: List[dict] = []
    for index, event in enumerate(response.get("events", [])):
        message = (event.get("message") or "").strip()
        payload: Dict[str, Any] = {}

        if message.startswith("{") and message.endswith("}"):
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                payload = {}

        event_type = payload.get("event_type") or payload.get("type") or "log"
        service_name = payload.get("service") or payload.get("service_name") or payload.get("root") or "system"
        severity = str(payload.get("severity") or "INFO").upper()
        if severity not in {"ERROR", "WARN", "INFO", "DEBUG"}:
            severity = "INFO"

        log_entries.append(
            {
                "id": f"log-{event.get('eventId', index)}",
                "timestamp": to_iso_timestamp(event.get("timestamp")),
                "service": str(service_name),
                "level": severity,
                "message": payload.get("message") or event_type.replace("_", " ").title(),
                "details": message[:280],
            }
        )

    return log_entries


def build_impact_rows(services: List[dict], logs: List[dict]) -> List[dict]:
    trend_bins: Dict[str, List[int]] = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])

    for entry in logs:
        timestamp = entry.get("timestamp")
        service_name = entry.get("service")
        if not timestamp or not service_name:
            continue

        try:
            log_time = datetime.fromisoformat(timestamp)
        except ValueError:
            continue

        age_hours = int((datetime.now(timezone.utc) - log_time).total_seconds() // 3600)
        bucket = max(0, min(6, 6 - age_hours))
        trend_bins[service_name][bucket] += 1

    impact_rows: List[dict] = []
    for service in services:
        impact_rows.append(
            {
                "service": service["name"],
                "impactScore": service["impactScore"],
                "blastRadius": service["blastRadius"],
                "severity": service["severity"],
                "status": service["finalHealth"],
                "trend": trend_bins.get(service["name"], [0, 0, 0, 0, 0, 0, 0]),
                "incidents": sum(trend_bins.get(service["name"], [])),
            }
        )

    return sorted(impact_rows, key=lambda item: item["impactScore"], reverse=True)


def build_graph_view(
    dependency_graph: Dict[str, List[str]],
    services: List[dict],
) -> dict:
    levels = compute_levels(dependency_graph)
    grouped: Dict[int, List[dict]] = defaultdict(list)

    for service in services:
        grouped[levels.get(service["name"], 0)].append(service)

    highest_level = max(levels.values(), default=0)
    nodes: List[dict] = []

    for level, layer in grouped.items():
        spacing = 240
        top_offset = 100
        width = (len(layer) - 1) * spacing

        for index, service in enumerate(layer):
            nodes.append(
                {
                    "id": service["name"],
                    "data": {
                        "label": service["name"],
                        "status": service["finalHealth"],
                        "metrics": service["metrics"],
                        "rootCause": service["rootCause"],
                        "confidence": service["confidence"],
                        "impactScore": service["impactScore"],
                    },
                    "position": {
                        "x": index * spacing - width / 2,
                        "y": top_offset + (highest_level - level) * 160,
                    },
                }
            )

    edges: List[dict] = []
    for service_name, dependencies in dependency_graph.items():
        for dependency in dependencies:
            edges.append(
                {
                    "id": f"{service_name}-{dependency}",
                    "source": service_name,
                    "target": dependency,
                    "animated": True,
                }
            )

    return {"nodes": nodes, "edges": edges}


def build_dashboard_snapshot() -> dict:
    started_at = time.perf_counter()

    try:
        dependency_graph, dependent_graph = load_dependency_graph()
        state_items = load_state_items()
        services = build_service_set(dependency_graph, state_items)

        local_state: Dict[str, str] = {}
        metrics_by_service: Dict[str, dict] = {}
        for service in services:
            item = state_items.get(service, {})
            metrics = item.get("metrics") or {}
            metrics_by_service[service] = metrics

            stored_local = item.get("local_state") or item.get("localState")
            local_state[service] = normalize_state(stored_local) if stored_local else evaluate_health(metrics)

        final_state = propagate_states(dependency_graph, dependent_graph, local_state)
        root_failures = detect_root_failures(dependency_graph, final_state)
        logs = query_recent_logs()

        service_rows: List[dict] = []
        for service in services:
            dependencies = dependency_graph.get(service, [])
            dependents = dependent_graph.get(service, [])
            final = final_state.get(service, "UNKNOWN")
            local = local_state.get(service, "UNKNOWN")
            propagated = final != local
            blast_radius = count_blast_radius(service, dependent_graph)
            root_cause = service in root_failures
            severity = severity_for_service(final, root_cause)
            impact_score = (SERVICE_WEIGHTS.get(service, 1) * max(1, blast_radius + 1)) + (6 if final == "FAILED" else 3 if final == "DEGRADED" else 0)

            service_rows.append(
                {
                    "name": service,
                    "localHealth": local.lower(),
                    "finalHealth": final.lower(),
                    "metrics": metrics_by_service.get(service, {}),
                    "dependencies": dependencies,
                    "dependents": dependents,
                    "rootCause": root_cause,
                    "severity": severity,
                    "confidence": confidence_score(dependencies, root_cause, propagated, final),
                    "impactScore": impact_score,
                    "blastRadius": blast_radius,
                    "propagated": propagated,
                }
            )

        alerts = []
        for service in service_rows:
            if service["finalHealth"] == "healthy":
                continue

            alerts.append(
                {
                    "id": f"alert-{service['name']}",
                    "title": f"{service['name']} root cause detected" if service["rootCause"] else f"{service['name']} propagation impact",
                    "severity": service["severity"],
                    "status": "active" if service["finalHealth"] != "healthy" else "resolved",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "affectedServices": [service["name"], *service["dependents"]][:5],
                    "rootCause": service["name"] if service["rootCause"] else (service["dependencies"][0] if service["dependencies"] else service["name"]),
                    "confidence": service["confidence"],
                    "summary": f"{service['name']} is {service['finalHealth']} and affecting downstream services.",
                }
            )

        impact = build_impact_rows(service_rows, logs)
        graph = build_graph_view(dependency_graph, service_rows)

        summary = {
            "totalServices": len(service_rows),
            "healthy": sum(1 for service in service_rows if service["finalHealth"] == "healthy"),
            "degraded": sum(1 for service in service_rows if service["finalHealth"] == "degraded"),
            "failed": sum(1 for service in service_rows if service["finalHealth"] == "failed"),
            "criticalAlerts": sum(1 for alert in alerts if alert["severity"] == "critical"),
            "activeAlerts": sum(1 for alert in alerts if alert["status"] == "active"),
        }

        return {
            "summary": summary,
            "services": service_rows,
            "alerts": alerts,
            "logs": logs,
            "impact": impact,
            "graph": graph,
            "lastSyncedAt": datetime.now(timezone.utc).isoformat(),
            "connectionState": "live",
            "liveLatencyMs": round((time.perf_counter() - started_at) * 1000),
            "localState": local_state,
            "finalState": final_state,
            "rootFailures": root_failures,
        }
    except (BotoCoreError, ClientError) as error:
        return {
            "summary": {
                "totalServices": 0,
                "healthy": 0,
                "degraded": 0,
                "failed": 0,
                "criticalAlerts": 0,
                "activeAlerts": 0,
            },
            "services": [],
            "alerts": [],
            "logs": [],
            "impact": [],
            "graph": {"nodes": [], "edges": []},
            "lastSyncedAt": datetime.now(timezone.utc).isoformat(),
            "connectionState": "offline",
            "liveLatencyMs": round((time.perf_counter() - started_at) * 1000),
            "localState": {},
            "finalState": {},
            "rootFailures": [],
            "error": str(error),
        }


@app.post("/metrics")
def ingest_metrics(service_name: str, metrics: ServiceMetrics):
    metrics_dict = metrics.dict()
    local_state = evaluate_health(metrics_dict)

    dependency_graph, dependent_graph = load_dependency_graph()
    state_items = load_state_items()
    services = build_service_set(dependency_graph, state_items)

    current_local_state: Dict[str, str] = {}
    for service in services:
        item = state_items.get(service, {})
        stored_local = item.get("local_state") or item.get("localState")
        stored_metrics = item.get("metrics") or {}
        current_local_state[service] = normalize_state(stored_local) if stored_local else evaluate_health(stored_metrics)

    current_local_state[service_name] = local_state
    final_state = propagate_states(dependency_graph, dependent_graph, current_local_state)
    root_failures = detect_root_failures(dependency_graph, final_state)

    try:
        state_table.put_item(
            Item={
                "service_name": service_name,
                "local_state": local_state,
                "final_state": final_state.get(service_name, local_state),
                "metrics": metrics_dict,
                "root_failure": service_name in root_failures,
                "last_updated": int(time.time()),
            }
        )
    except (BotoCoreError, ClientError) as error:
        return {"status": "error", "message": str(error)}

    return {
        "status": "ok",
        "service": service_name,
        "localState": local_state,
        "finalState": final_state,
        "rootFailures": root_failures,
    }


@app.get("/state")
def get_system_state():
    return build_dashboard_snapshot()


@app.get("/graph")
def get_graph():
    snapshot = build_dashboard_snapshot()
    return {"graph": snapshot["graph"]}


@app.get("/alerts")
def get_alerts():
    snapshot = build_dashboard_snapshot()
    return {"alerts": snapshot["alerts"]}


@app.get("/logs")
def get_logs():
    snapshot = build_dashboard_snapshot()
    return {"logs": snapshot["logs"]}


@app.get("/impact")
def get_impact():
    snapshot = build_dashboard_snapshot()
    return {"impact": snapshot["impact"]}
