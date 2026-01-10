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
    For each root cause, find the longest downstream path.
    """

    def dfs(service, path, visited):
        visited.add(service)
        longest = path.copy()

        for downstream, upstreams in dependency_graph.items():
            if service in upstreams and downstream not in visited:
                candidate = dfs(downstream, path + [downstream], visited)
                if len(candidate) > len(longest):
                    longest = candidate

        visited.remove(service)
        return longest

    critical_paths = {}

    for root in root_causes:
        critical_paths[root] = dfs(root, [root], set())

    return critical_paths
