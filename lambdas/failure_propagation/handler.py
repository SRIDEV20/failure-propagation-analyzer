import json
import os
import time

import boto3

from engine.analysis import find_critical_paths, find_root_causes
from engine.health_rules import evaluate_health
from engine.impact import calculate_impact_scores, rank_services_by_impact
from engine.propagation import propagate_failures


dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")
sns = boto3.client("sns", region_name="ap-south-1")

SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
STATE_TABLE_NAME = os.getenv("STATE_TABLE_NAME", "service_state")
GRAPH_TABLE_NAME = os.getenv("GRAPH_TABLE_NAME", "service_dependency_graph")
TABLE_ALIAS_CANDIDATES = {
    "state": [STATE_TABLE_NAME, "service_state", "service_state_cdk"],
    "graph": [GRAPH_TABLE_NAME, "service_dependency_graph", "service_dependency_graph_cdk"],
}


def resolve_table(table_names: list[str]):
    candidates = [name for name in dict.fromkeys(name for name in table_names if name)]
    if not candidates:
        raise ValueError("No DynamoDB table names were provided")

    for table_name in candidates:
        table = dynamodb.Table(table_name)

        try:
            if table.scan(Limit=1).get("Items"):
                return table
        except Exception:
            continue

    return dynamodb.Table(candidates[0])


state_table = resolve_table(TABLE_ALIAS_CANDIDATES["state"])
graph_table = resolve_table(TABLE_ALIAS_CANDIDATES["graph"])


def log(event_type: str, payload: dict):
    print(json.dumps({
        "event_type": event_type,
        "timestamp": int(time.time()),
        **payload,
    }))


def compute_system_severity(final_health: dict) -> str:
    affected = sum(1 for s in final_health.values() if s in ("DEGRADED", "FAILED"))
    failed = sum(1 for s in final_health.values() if s == "FAILED")

    if failed >= 2 or affected >= 3:
        return "CRITICAL"
    return "LOW"


def service_severity_for_state(service_state: str, is_root_failure: bool) -> str:
    if is_root_failure or service_state == "FAILED":
        return "CRITICAL"
    if service_state == "DEGRADED":
        return "WARNING"
    return "INFO"


def compute_severity(final_health: dict) -> str:
    return compute_system_severity(final_health)


# 🔥 Fallback graph (if DynamoDB empty)
def get_dependency_graph():
    items = graph_table.scan().get("Items", [])

    if not items:
        log("fallback_graph_used", {})
        return {
            "frontend": ["backend"],
            "backend": ["database"],
            "database": []
        }

    graph = {}
    for item in items:
        graph[item["service_name"]] = item.get("depends_on", [])

    return graph


def resolve_services(graph):
    names = set(graph.keys())
    for deps in graph.values():
        names.update(deps)
    return list(names)


# 🔥 Force failure (for demo)
def generate_metrics(services):
    metrics = {}
    for s in services:
        metrics[s] = {
            "latency_ms": 3000,
            "error_rate": 0.9,
            "timeout": False
        }
    return metrics


# ✅ FINAL ALERT FORMAT (WHAT YOU WANT)
def publish_alert(severity, roots, final_health, critical_paths):
    if severity != "CRITICAL":
        log("alert_skipped", {"severity": severity})
        return False

    if not SNS_TOPIC_ARN:
        log("sns_missing", {})
        return False

    # Clean roots
    roots = sorted(set(roots))

    # ONLY impacted services (not all)
    affected = sorted([
        svc for svc, state in final_health.items()
        if state in ("DEGRADED", "FAILED")
    ])

    # 🔥 Clean critical path formatting
    path_lines = []
    for root, path in critical_paths.items():
        path_lines.append(" → ".join(path))

    formatted_message = f"""
🚨 Failure Propagation Alert

Severity: {severity}

Root Failures:
{chr(10).join(f"- {r}" for r in roots)}

Affected Services:
{chr(10).join(f"- {s}" for s in affected)}

Service Impact Paths:
{chr(10).join(f"- {p}" for p in path_lines)}
"""

    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="[CRITICAL] Failure Propagation Alert",
        Message=formatted_message
    )

    log("alert_sent", {
        "severity": severity,
        "roots": roots,
        "affected": affected
    })

    return True


def persist_service_state(graph, initial_health, final_health, roots, impact_scores, critical_paths):
    updated_at = int(time.time())
    for service in sorted(final_health.keys()):
        service_state = final_health.get(service, "UNKNOWN")
        is_root_failure = service in roots
        severity = service_severity_for_state(service_state, is_root_failure)

        state_table.put_item(
            Item={
                "service_name": service,
                "local_state": initial_health.get(service, "UNKNOWN"),
                "final_state": service_state,
                "root_failure": is_root_failure,
                "severity": severity,
                "impact_score": impact_scores.get(service, 0),
                "base_impact_score": impact_scores.get(service, 0),
                "critical_path": critical_paths.get(service, []),
                "dependency_count": len(graph.get(service, [])),
                "last_updated": updated_at,
            }
        )


def lambda_handler(event, context):
    log("lambda_start", {"event": event or {}})

    graph = get_dependency_graph()
    services = resolve_services(graph)

    metrics = generate_metrics(services)
    log("metrics_generated", metrics)

    initial_health = {
        s: evaluate_health(metrics[s]).value
        for s in services
    }

    final_health = propagate_failures(graph, initial_health)

    roots = find_root_causes(graph, final_health)
    critical_paths = find_critical_paths(graph, roots)
    impact_scores = calculate_impact_scores(final_health)
    ranked = rank_services_by_impact(impact_scores)

    severity = compute_severity(final_health)

    persist_service_state(graph, initial_health, final_health, roots, impact_scores, critical_paths)

    log("analysis", {
        "severity": severity,
        "roots": roots,
        "impact": ranked
    })

    alert_sent = publish_alert(severity, roots, final_health, critical_paths)

    return {
        "severity": severity,
        "alert_sent": alert_sent
    }