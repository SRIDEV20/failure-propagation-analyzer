from collections import deque
from engine.health_rules import HealthState


SEVERITY_ORDER = {
    HealthState.HEALTHY: 0,
    HealthState.DEGRADED: 1,
    HealthState.FAILED: 2,
}


def worse_state(a: HealthState, b: HealthState) -> HealthState:
    return a if SEVERITY_ORDER[a] >= SEVERITY_ORDER[b] else b


def propagate_failures(dependency_graph: dict, initial_health: dict) -> dict:
    """
    Propagate failures downstream based on dependency graph.
    """

    final_health = {
        service: HealthState[state]
        for service, state in initial_health.items()
    }

    # Track which services were GENUINELY failed locally (not just failed
    # because of propagation). Only these get to propagate FAILED to their
    # direct dependents. Anything beyond that first hop dampens to DEGRADED,
    # so a single outage can't cascade as a hard FAILED across the whole
    # graph (false amplification).
    locally_failed = {
        service for service, state in final_health.items()
        if state == HealthState.FAILED
    }

    queue = deque(final_health.keys())

    while queue:
        service = queue.popleft()
        service_state = final_health[service]

        # Only propagate if degraded or failed
        if service_state == HealthState.HEALTHY:
            continue

        for downstream, upstreams in dependency_graph.items():
            if service not in upstreams:
                continue

            current_state = final_health[downstream]

            if service in locally_failed:
                propagated_state = HealthState.FAILED
            else:
                propagated_state = HealthState.DEGRADED

            new_state = worse_state(current_state, propagated_state)

            if new_state != current_state:
                final_health[downstream] = new_state
                queue.append(downstream)

    return {svc: state.value for svc, state in final_health.items()}