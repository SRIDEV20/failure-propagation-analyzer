# failure-propagation-analyzer
Event-driven system for detecting cascading failures and identifying root causes in distributed architectures

An AWS-native backend system for detecting service failures, propagating their impact across dependencies, identifying root causes, and generating severity-based alerts with confidence scoring.

This project simulates how modern distributed systems analyze cascading failures and assist on-call engineers with fast, deterministic, and explainable Root Cause Analysis (RCA).

---

## Problem Statement

In microservice architectures, a single service failure can cascade across multiple dependent services, making it difficult to:

- Identify the true root cause
- Understand the blast radius of impact
- Prioritize incidents correctly
- Avoid alert fatigue

Traditional monitoring systems surface symptoms but fail to explain causality.

This system addresses that gap by:
- Modeling service dependencies explicitly
- Propagating failures deterministically
- Separating cause from impact
- Alerting only when escalation is justified

---

## High-Level Architecture

### Core Components
- **AWS Lambda** – Failure analysis and propagation engine
- **Amazon DynamoDB** – Service state and dependency graph
- **Amazon EventBridge** – Scheduled system-wide analysis
- **Amazon SNS** – Severity-based alerting
- **Amazon CloudWatch** – Structured logs and observability

### Execution Modes
- **Real-time ingestion** (metric-triggered)
- **Scheduled analysis** (periodic consistency checks)

---

## Core Features

- Service health evaluation using latency, error rate, and timeout signals
- Dependency-aware failure propagation using BFS traversal
- Root cause identification (primary vs secondary failures)
- Blast radius computation
- Severity classification (LOW / MEDIUM / CRITICAL)
- Confidence scoring (0–100) for incident prioritization
- Alert deduplication and suppression
- Structured JSON logging for traceability

---

## Failure Propagation Logic

1. Detect locally unhealthy services
2. Load dependency graph from DynamoDB
3. Traverse downstream dependencies using BFS
4. Mark impacted services as unhealthy
5. Prevent duplicate propagation
6. Preserve distinction between local and propagated failures

This ensures deterministic, explainable failure analysis without false amplification.

---

## Root Cause Classification

Each service failure is classified as:

- **PRIMARY** – Service failed independently (no unhealthy upstream dependencies)
- **SECONDARY** – Service failed due to upstream propagation

This allows engineers to immediately separate cause from impact during incident response.

---

## Alerting & Observability

Alerts are emitted only when:
- Severity is **MEDIUM** or **CRITICAL**
- Severity escalates compared to previous state

CloudWatch logs are structured and include:
- `lambda_start`
- `analysis_complete`
- `failure_classification`
- `alert_sent`
- `alert_suppressed`

This provides full auditability and debugging visibility.

---

## Confidence Scoring

Each incident is assigned a confidence score (0–100) based on:
- Severity level
- Blast radius size
- Presence of primary failures
- Degree of propagated impact

The score helps teams prioritize incidents instead of reacting blindly to raw alerts.

---

## DynamoDB Data Model

### `service_dependency_graph`
| Attribute | Description |
|--------|-------------|
| service_name (PK) | Service identifier |
| depends_on | Downstream dependencies |

### `service_state`
| Attribute | Description |
|--------|-------------|
| service_name (PK) | Service identifier |
| local_state | HEALTHY / UNHEALTHY |
| final_state | After propagation |
| failure_type | PRIMARY / SECONDARY |
| severity | LOW / MEDIUM / CRITICAL |
| confidence_score | 0–100 |
| metrics | Latest metrics snapshot |
| last_updated | Epoch timestamp |

---

## End-to-End Flow

1. Metrics ingested via Lambda or scheduled trigger
2. Health evaluated per service
3. Dependency graph loaded
4. Failures propagated downstream
5. Root causes identified
6. Severity and confidence computed
7. Alerts sent (if required)
8. State persisted to DynamoDB
9. Structured logs emitted to CloudWatch

---


## How to Run / Test

### Manual Lambda Test Payload
```json
{
  "service_name": "inventory-service",
  "metrics": {
    "timeout": true
  }
}
