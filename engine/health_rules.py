from enum import Enum


class HealthState(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


def evaluate_health(metrics: dict) -> HealthState:
    """
    Evaluate health of a service based on its metrics.

    Rules:
    - timeout == True  -> FAILED
    - latency > 1000ms -> DEGRADED
    - error_rate > 20% -> DEGRADED
    - otherwise        -> HEALTHY
    """

    # Hard failure: service not responding
    if metrics.get("timeout") is True:
        return HealthState.FAILED

    latency = metrics.get("latency_ms")
    error_rate = metrics.get("error_rate")

    # Latency-based degradation
    if latency is not None and latency > 1000:
        return HealthState.DEGRADED

    # Error burst degradation
    if error_rate is not None and error_rate > 0.2:
        return HealthState.DEGRADED

    return HealthState.HEALTHY
