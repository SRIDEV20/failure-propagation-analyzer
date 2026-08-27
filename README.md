# failure-propagation-analyzer

Event-driven system for detecting cascading failures and identifying root causes in distributed architectures

An AWS system for detecting service failures, propagating their impact across dependencies, identifying root causes, and generating severity-based alerts with confidence scoring.

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

## What it actually does

1. **Watches** each service's health from its metrics (latency, error rate, timeouts)
2. **Propagates** failures downstream through an explicit dependency graph using BFS
3. **Distinguishes** root cause (the original failure) from secondary impact (everything knocked over by it)
4. **Scores** severity and blast radius per incident
5. **Alerts** by email (SNS) when severity crosses a real threshold
6. **Visualizes** the whole live system on a React dashboard — dependency graph, alerts, impact ranking, and logs

No machine learning, no black box — every classification is a traceable, deterministic rule. That's a deliberate choice: on-call engineers need to trust *why* an alert fired, not just that a model said so.

---

## Architecture

```
                      ┌───────────────────────┐
   Metric event ────▶ │   Analyzer Lambda      │◀──── EventBridge
   (real-time)        │   (handler.py)         │      (every 5 min,
                       └──────────┬─────────────┘       scheduled)
                                  │ read + write
                       ┌──────────▼─────────────┐
                       │       DynamoDB          │
                       │  service_dependency_    │
                       │  graph  +  service_     │
                       │  state                  │
                       └──────────┬─────────────┘
                                  │ read-only
                       ┌──────────▼─────────────┐
   React dashboard ───▶│   API Lambda (FastAPI)  │────▶ SNS (email alerts)
   (polls every 15s)   │   (api.py, via Mangum)  │
                       └─────────────────────────┘
                            ▲
                            │ HTTPS
                       API Gateway
```

Two independent Lambdas share the same core decision logic (`engine/`), but serve completely different purposes:

- **Analyzer Lambda** — the write path. Triggered by EventBridge (scheduled) or a direct real-time invocation carrying a specific service's new metrics. Runs the full pipeline, persists results to DynamoDB, and publishes an alert to SNS when severity is CRITICAL.
- **API Lambda** — the read path, sitting behind API Gateway. Never writes anything. Instead of trusting whatever the analyzer last saved, it **independently re-derives** propagation and root-cause analysis from the raw DynamoDB data on every request — so the dashboard is always self-consistent, even if the analyzer hasn't run recently.

Infrastructure is defined as code with **AWS CDK (Python)** — both Lambdas, two DynamoDB tables, an SNS topic, an EventBridge schedule, and an API Gateway REST API, all provisioned or referenced through `infra/failure_propagation_infra/stack.py`.

---

## The core engine (`engine/`)

Pure Python, zero AWS dependencies — fully unit-testable and shared by the CLI, both Lambdas, and (independently re-implemented) by the API layer.

| File | Job |
|---|---|
| `health_rules.py` | Turns one service's raw metrics into HEALTHY / DEGRADED / FAILED |
| `propagation.py` | BFS that spreads failures downstream through the dependency graph |
| `analysis.py` | Separates root cause from secondary impact; finds the deepest downstream blast-radius chain(s) per root cause |
| `impact.py` | Scores each unhealthy service by weighted importance and blast radius |

### Failure propagation rules

Propagation isn't "everything downstream becomes equally broken." It follows a deliberate attenuation rule to avoid false amplification:

- A service that is **genuinely, locally unhealthy** (its own metrics tripped a rule) can propagate a hard **FAILED** state to its **direct** dependents.
- Beyond that first hop, severity dampens to **DEGRADED** — so a single outage cascades realistically instead of turning the entire graph red.

```
inventory-db  (FAILED — genuine failure)
   └── inventory-service   (FAILED — 1 hop, inherits full severity)
         └── order-service  (DEGRADED — 2 hops, dampened)
               └── audit-service          (DEGRADED — 3 hops)
               └── notification-service   (DEGRADED — 3 hops)
```

### Root cause vs. secondary impact

A service is classified as a **root cause** if none of the services it depends on are also unhealthy. Everything else that's unhealthy is a **secondary failure** — a victim of something upstream, not the origin.

### Critical paths

For each root cause, the system reports every downstream chain tied for the deepest impact — not just one arbitrarily-picked branch. If a failure forks (one service has multiple dependents), every branch tied for maximum depth is reported, so no equally-affected path is silently dropped.

---

## Execution modes

- **Real-time ingestion** — invoke with a specific service's new metrics:
  ```json
  { "service_name": "inventory-db", "metrics": { "timeout": true } }
  ```
  Only that one service's metrics are updated; every other service keeps its last-known state.

- **Scheduled analysis** — EventBridge invokes with `{"run_mode": "scheduled"}` every 5 minutes. The system re-evaluates every service from its **last-known stored metrics** in DynamoDB (not fabricated data), so state genuinely persists and is re-checked between runs rather than being reset each cycle.

---

## Alerting

An alert is only published to SNS when overall severity is **CRITICAL** (2+ services FAILED, or 3+ services affected in total). The formatted email includes the root cause(s), every affected service, and every critical impact path:

```
🚨 Failure Propagation Alert

Severity: CRITICAL

Root Failures:
- inventory-db

Affected Services:
- audit-service
- inventory-db
- inventory-service
- notification-service
- order-service

Service Impact Paths:
- inventory-db → inventory-service → order-service → audit-service
- inventory-db → inventory-service → order-service → notification-service
```

---

## Frontend

A React + TypeScript dashboard (Vite, `frontend/`) that visualizes the live system:

- **Overview** — system-wide summary
- **Graph** — the dependency graph rendered with `reactflow`, nodes colored live by health, click-to-inspect metrics/confidence/impact per service
- **Alerts** — active alerts with root cause and confidence
- **Impact** — services ranked by impact score
- **Logs** — recent CloudWatch log events

The whole frontend is driven by a single shared data source: `DashboardContext` polls the API's `/state` endpoint every 15 seconds and distributes the result to every page via React Context — one network call powers the entire dashboard rather than each page fetching independently.

Currently runs locally (`npm run dev`); not yet deployed to a public host.

---

## DynamoDB data model

### `service_dependency_graph`
| Attribute | Description |
|---|---|
| `service_name` (PK) | Service identifier |
| `depends_on` | List of upstream services this one depends on |

### `service_state`
| Attribute | Description |
|---|---|
| `service_name` (PK) | Service identifier |
| `metrics` | Latest metrics snapshot (persisted, so scheduled runs can recall it) |
| `local_state` | Health from this service's own metrics, before propagation |
| `final_state` | Health after propagation |
| `root_failure` | `true` if this service is a root cause |
| `severity` | INFO / WARNING / CRITICAL |
| `impact_score` | Weighted importance-based severity score |
| `critical_path` | Deepest downstream impact chain(s), if this service is a root cause |
| `dependency_count` | Number of services this one depends on |
| `last_updated` | Epoch timestamp |

---

## How to run / test

### Local CLI (no AWS needed)
```bash
python main.py
python main.py --fail order-service
```
Uses `data/dependencyGraph.json` and `scenarios/sample_metrics.json` for a fully local, no-AWS test of the propagation/root-cause logic.

### Manual Lambda test payloads
```json
// Inject a failure
{ "service_name": "inventory-db", "metrics": { "timeout": true } }

// Reset back to healthy
{ "service_name": "inventory-db", "metrics": {} }

// Simulate a scheduled EventBridge cycle
{ "run_mode": "scheduled" }
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Known trade-offs and limitations

Being upfront about these rather than hiding them:

- **Duplicate propagation logic** — `engine/propagation.py` and `api.py`'s `propagate_states()` implement the same idea independently rather than sharing one function. Similarly, `api.py` maintains its own copy of `evaluate_health()` instead of importing from `engine/health_rules.py`.
- **No alert deduplication on escalation** — an alert fires whenever severity is CRITICAL, not only when it *newly becomes* CRITICAL. An unresolved incident will re-alert on every scheduled cycle until it's cleared.
- **Hardcoded service weights** (`SERVICE_WEIGHTS` in `impact.py`) — a stand-in for a real service catalog / CMDB.
- **`find_critical_paths` is O(V×E)** — fine at this scale, would need a reverse-adjacency approach to scale to a large graph.
- **Services are conceptual, not real deployed applications** — metrics are supplied manually (via test payloads) rather than sourced from real telemetry like CloudWatch Metrics or an APM tool, since there's no actual running microservice mesh behind the graph.

---

## Tech stack

**Backend:** Python 3.12, AWS Lambda, DynamoDB, EventBridge, SNS, API Gateway, FastAPI + Mangum, AWS CDK (Python)
**Frontend:** React, TypeScript, Vite, React Router, Recharts, React Flow, Axios