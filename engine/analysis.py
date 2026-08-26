from engine.health_rules import HealthState


def find_root_causes(dependency_graph: dict, final_health: dict) -> list:
    """
    Identify root cause services.
    """

    roots = []

    for service, state in final_health.items():
        if state == "HEALTHY":
            continue

        upstreams = dependency_graph.get(service, [])

        caused_by_upstream = False
        for upstream in upstreams:
            upstream_state = final_health.get(upstream)
            if upstream_state in ("DEGRADED", "FAILED"):
                caused_by_upstream = True
                break

        if not caused_by_upstream:
            roots.append(service)

    return roots
def find_critical_paths(dependency_graph: dict, root_causes: list) -> dict:
    """
    For each root cause, find every downstream path tied for the longest
    length (not just one arbitrarily-picked branch). When a service has
    multiple dependents, the graph forks into separate branches -- all
    branches tied for the maximum depth are returned, so no equally-affected
    branch is silently dropped. Iteration is sorted for deterministic output
    regardless of the source dictionary's ordering (e.g. a DynamoDB scan).
    """

    def dfs(service, path, visited):
        next_visited = visited | {service}
        branch_paths = []

        for downstream, upstreams in sorted(dependency_graph.items()):
            if service in upstreams and downstream not in next_visited:
                branch_paths.extend(dfs(downstream, path + [downstream], next_visited))

        if not branch_paths:
            return [path]

        max_len = max(len(p) for p in branch_paths)
        return [p for p in branch_paths if len(p) == max_len]

    critical_paths = {}

    for root in root_causes:
        critical_paths[root] = dfs(root, [root], set())

    return critical_paths
