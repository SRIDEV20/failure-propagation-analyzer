import boto3
import time
import json
import os
from collections import deque, defaultdict
from decimal import Decimal

# -----------------------------
# AWS Clients
# -----------------------------
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
sns = boto3.client("sns", region_name="ap-south-1")

# -----------------------------
# Environment Configuration
# -----------------------------
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")

STATE_TABLE_NAME = os.getenv("STATE_TABLE_NAME", "service_state")
GRAPH_TABLE_NAME = os.getenv("GRAPH_TABLE_NAME", "service_dependency_graph")

state_table = dynamodb.Table(STATE_TABLE_NAME)
graph_table = dynamodb.Table(GRAPH_TABLE_NAME)

ALERT_STATE_KEY = "__ALERT_STATE__"

# -----------------------------
# DynamoDB Safe Converter
# -----------------------------
def to_dynamodb_safe(obj):
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: to_dynamodb_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_dynamodb_safe(v) for v in obj]
    return obj

# -----------------------------
# Logging Helper
# -----------------------------
def log(event_type: str, payload: dict):
    print(json.dumps({
        "event_type": event_type,
        "timestamp": int(time.time()),
        **payload
    }))

# -----------------------------
# Health Evaluation
# -----------------------------
def evaluate_health(metrics: dict) -> str:
    if not metrics:
        return "HEALTHY"
    if metrics.get("timeout") is True:
        return "UNHEALTHY"
    if metrics.get("latency_ms", 0) > 1000:
        return "UNHEALTHY"
    if metrics.get("error_rate", 0) > 0.2:
        return "UNHEALTHY"
    return "HEALTHY"

# -----------------------------
# Severity Logic
# -----------------------------
def compute_severity(final_state: dict) -> str:
    affected = sum(1 for s in final_state.values() if s == "UNHEALTHY")
    if affected >= 5:
        return "CRITICAL"
    elif affected >= 3:
        return "MEDIUM"
    return "LOW"

# -----------------------------
# Confidence Scoring
# -----------------------------
def compute_confidence_score(severity, primary, secondary, final_state):
    score = 0

    severity_weight = {
        "LOW": 20,
        "MEDIUM": 50,
        "CRITICAL": 80
    }
    score += severity_weight.get(severity, 0)

    blast_radius = len([s for s in final_state.values() if s == "UNHEALTHY"])
    score += min(blast_radius * 5, 30)

    if primary:
        score += 10
    if secondary:
        score += 10

    return min(score, 100)

# -----------------------------
# Alert State Helpers
# -----------------------------
def get_last_alerted_severity():
    try:
        resp = state_table.get_item(Key={"service_name": ALERT_STATE_KEY})
        return resp.get("Item", {}).get("last_alerted_severity")
    except Exception:
        return None

def update_last_alerted_severity(severity):
    state_table.put_item(
        Item={
            "service_name": ALERT_STATE_KEY,
            "last_alerted_severity": severity,
            "last_updated": int(time.time())
        }
    )

# -----------------------------
# SNS Alert Logic
# -----------------------------
def send_alert_if_needed(severity, root_failures, final_state):
    if severity not in ["MEDIUM", "CRITICAL"]:
        return False

    if not SNS_TOPIC_ARN:
        log("alert_skipped", {"reason": "SNS_TOPIC_ARN not set"})
        return False

    last = get_last_alerted_severity()
    if last == severity:
        log("alert_suppressed", {"severity": severity})
        return False

    affected = [s for s, st in final_state.items() if st == "UNHEALTHY"]

    message = (
        f"🚨 Failure Propagation Alert\n\n"
        f"Severity: {severity}\n"
        f"Root Failures: {root_failures}\n"
        f"Affected Services:\n" + "\n".join(affected)
    )

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject=f"[{severity}] Failure Propagation",
        Message=message
    )

    update_last_alerted_severity(severity)
    log("alert_sent", {"severity": severity})
    return True

# -----------------------------
# Load Dependency Graph
# -----------------------------
def load_dependency_graph():
    items = graph_table.scan().get("Items", [])
    graph = {}
    upstream = defaultdict(list)

    for item in items:
        svc = item["service_name"]
        deps = item.get("depends_on", [])
        graph[svc] = deps
        for d in deps:
            upstream[d].append(svc)

    return graph, upstream

# -----------------------------
# Load Existing State
# -----------------------------
def load_existing_state():
    items = state_table.scan().get("Items", [])
    state, metrics = {}, {}

    for item in items:
        svc = item["service_name"]
        if svc == ALERT_STATE_KEY:
            continue
        state[svc] = item.get("local_state", "HEALTHY")
        metrics[svc] = item.get("metrics", {})
    return state, metrics

# -----------------------------
# Lambda Handler
# -----------------------------
def lambda_handler(event, context):

    log("lambda_start", {"event": event})

    graph, upstream = load_dependency_graph()
    service_state, service_metrics = load_existing_state()

    run_mode = event.get("run_mode", "ingest")

    if run_mode == "scheduled":
        for s, m in service_metrics.items():
            service_state[s] = evaluate_health(m)
        mode = "scheduled"
    elif run_mode == "ingest":
        svc = event.get("service_name")
        metrics = event.get("metrics")

        if not svc or not metrics:
            raise ValueError("service_name and metrics are required")

        service_metrics[svc] = metrics
        service_state[svc] = evaluate_health(metrics)
        mode = "ingest"
    else:
        raise ValueError(f"Unknown run_mode: {run_mode}")

    # -----------------------------
    # Failure Propagation
    # -----------------------------
    final_state = service_state.copy()
    q = deque([s for s, st in service_state.items() if st == "UNHEALTHY"])

    while q:
        cur = q.popleft()
        for d in graph.get(cur, []):
            if final_state.get(d) != "UNHEALTHY":
                final_state[d] = "UNHEALTHY"
                q.append(d)

    # -----------------------------
    # Root Cause Analysis
    # -----------------------------
    primary, secondary = [], []
    for s, st in service_state.items():
        if st != "UNHEALTHY":
            continue
        ups = upstream.get(s, [])
        if not any(service_state.get(u) == "UNHEALTHY" for u in ups):
            primary.append(s)
        else:
            secondary.append(s)

    severity = compute_severity(final_state)
    confidence = compute_confidence_score(
        severity, primary, secondary, final_state
    )

    alert_sent = send_alert_if_needed(severity, primary, final_state)

    log("analysis_complete", {
        "mode": mode,
        "severity": severity,
        "confidence_score": confidence,
        "primary_failures": primary,
        "secondary_failures": secondary,
        "alert_sent": alert_sent
    })

    # -----------------------------
    # Persist State
    # -----------------------------
    now = int(time.time())
    for s in final_state:
        state_table.put_item(
            Item={
                "service_name": s,
                "local_state": service_state.get(s, "HEALTHY"),
                "final_state": final_state.get(s, "HEALTHY"),
                "metrics": to_dynamodb_safe(service_metrics.get(s, {})),
                "severity": severity,
                "confidence_score": confidence,
                "last_updated": now
            }
        )

    return {
        "severity": severity,
        "confidence_score": confidence,
        "primary_failures": primary,
        "secondary_failures": secondary
    }
