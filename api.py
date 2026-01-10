from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, List
from collections import deque, defaultdict
import boto3
import time

app = FastAPI(title="Failure Propagation Analyzer")


# -----------------------------
# AWS DynamoDB Setup
# -----------------------------
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
state_table = dynamodb.Table("service_state")
graph_table = dynamodb.Table("service_dependency_graph")


# -----------------------------
# Data Models
# -----------------------------
class ServiceMetrics(BaseModel):
    latency_ms: Optional[int] = None
    error_rate: Optional[float] = None
    timeout: Optional[bool] = False


# -----------------------------
# Graph Loader (Day 18)
# -----------------------------
def load_dependency_graph():
    response = graph_table.scan()
    items = response.get("Items", [])

    dependency_graph: Dict[str, List[str]] = {}
    upstream_graph: Dict[str, List[str]] = defaultdict(list)

    for item in items:
        service = item["service_name"]
        depends_on = item.get("depends_on", [])

        # Convert DynamoDB list format → normal list
        downstreams = [d for d in depends_on]

        dependency_graph[service] = downstreams

        for downstream in downstreams:
            upstream_graph[downstream].append(service)

    return dependency_graph, upstream_graph


# -----------------------------
# In-memory State
# -----------------------------
SERVICE_STATE: Dict[str, str] = {}
FINAL_STATE: Dict[str, str] = {}


# -----------------------------
# Health Evaluation
# -----------------------------
def evaluate_health(metrics: dict) -> str:
    if metrics.get("timeout") is True:
        return "UNHEALTHY"

    latency = metrics.get("latency_ms")
    error_rate = metrics.get("error_rate")

    if latency is not None and latency > 1000:
        return "UNHEALTHY"

    if error_rate is not None and error_rate > 0.2:
        return "UNHEALTHY"

    return "HEALTHY"


# -----------------------------
# Failure Propagation
# -----------------------------
def propagate_unhealthy_states(dependency_graph):
    global FINAL_STATE

    FINAL_STATE = SERVICE_STATE.copy()
    queue = deque(svc for svc, st in SERVICE_STATE.items() if st == "UNHEALTHY")

    while queue:
        current = queue.popleft()
        for downstream in dependency_graph.get(current, []):
            if FINAL_STATE.get(downstream) != "UNHEALTHY":
                FINAL_STATE[downstream] = "UNHEALTHY"
                queue.append(downstream)


# -----------------------------
# Root Failure Detection
# -----------------------------
def detect_root_failures(upstream_graph):
    roots = []

    for service, state in SERVICE_STATE.items():
        if state != "UNHEALTHY":
            continue

        upstreams = upstream_graph.get(service, [])
        if not any(SERVICE_STATE.get(u) == "UNHEALTHY" for u in upstreams):
            roots.append(service)

    return roots


# -----------------------------
# DynamoDB Persistence
# -----------------------------
def persist_service_state(service_name: str, metrics: dict):
    state_table.put_item(
        Item={
            "service_name": service_name,
            "local_state": SERVICE_STATE.get(service_name),
            "final_state": FINAL_STATE.get(service_name),
            "metrics": metrics,
            "last_updated": int(time.time())
        }
    )


# -----------------------------
# API Endpoints
# -----------------------------
@app.post("/metrics")
def ingest_metrics(service_name: str, metrics: ServiceMetrics):
    metrics_dict = metrics.dict()

    SERVICE_STATE[service_name] = evaluate_health(metrics_dict)

    dependency_graph, upstream_graph = load_dependency_graph()

    propagate_unhealthy_states(dependency_graph)
    root_failures = detect_root_failures(upstream_graph)

    persist_service_state(service_name, metrics_dict)

    return {
        "status": "ok",
        "service": service_name,
        "local_state": SERVICE_STATE[service_name],
        "root_failures": root_failures,
        "final_state": FINAL_STATE
    }


@app.get("/state")
def get_system_state():
    dependency_graph, upstream_graph = load_dependency_graph()

    return {
        "local_state": SERVICE_STATE,
        "final_state": FINAL_STATE,
        "root_failures": detect_root_failures(upstream_graph)
    }
