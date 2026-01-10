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


def calculate_impact_scores(final_health: dict) -> dict:
    """
    Impact score = sum of weights of affected services.
    """

    impact_scores = {}

    for service, state in final_health.items():
        if state == "HEALTHY":
            continue

        weight = SERVICE_WEIGHTS.get(service, 1)
        impact_scores[service] = weight

    return impact_scores


def rank_services_by_impact(impact_scores: dict) -> list:
    """
    Rank services by descending impact score.
    """

    return sorted(
        impact_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
