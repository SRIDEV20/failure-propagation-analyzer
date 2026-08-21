SERVICE_WEIGHTS = {
    "api-gateway": 5,
    "order-service": 4,
    "payment-service": 4,
    "auth": 3,
    "inventory-service": 3,
    "notification-service": 2,
    "audit-service": 2,
    "user-db": 1,
    "inventory-db": 1,
    "external-payment-gateway": 1
}


def calculate_base_impact_scores(final_health: dict) -> dict:
    """
    Base impact score = the service weight for every unhealthy service.
    This is the value persisted in DynamoDB as impact_score for a service.
    """

    impact_scores = {}

    for service, state in final_health.items():
        if state == "HEALTHY":
            continue

        impact_scores[service] = SERVICE_WEIGHTS.get(service, 1)

    return impact_scores


def calculate_impact_scores(final_health: dict) -> dict:
    """
    Backward-compatible alias for the base impact score.
    """

    return calculate_base_impact_scores(final_health)


def calculate_operational_impact_scores(final_health: dict, blast_radius_by_service: dict[str, int] | None = None) -> dict:
    """
    Operational impact = base weight x downstream blast radius multiplier + degradation penalty.
    """

    blast_radius_by_service = blast_radius_by_service or {}
    operational_scores = {}

    for service, state in final_health.items():
        if state == "HEALTHY":
            continue

        base_score = SERVICE_WEIGHTS.get(service, 1)
        blast_radius = max(1, blast_radius_by_service.get(service, 0) + 1)
        penalty = 6 if state == "FAILED" else 3 if state == "DEGRADED" else 0
        operational_scores[service] = (base_score * blast_radius) + penalty

    return operational_scores


def rank_services_by_impact(impact_scores: dict) -> list:
    """
    Rank services by descending impact score.
    """

    return sorted(
        impact_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
