import json
import argparse
from engine.health_rules import evaluate_health
from engine.propagation import propagate_failures
from engine.analysis import find_root_causes, find_critical_paths
from engine.impact import calculate_impact_scores, rank_services_by_impact


def load_json(path: str) -> dict:
    with open(path, "r") as file:
        return json.load(file)


def simulate_failure(metrics_data: dict, service: str):
    metrics_data[service] = {
        "latency_ms": None,
        "error_rate": None,
        "timeout": True
    }


def main():
    parser = argparse.ArgumentParser(description="Failure Propagation Analyzer")
    parser.add_argument("--fail", help="Simulate failure of a service")
    args = parser.parse_args()

    dependency_graph = load_json("data/dependencyGraph.json")
    metrics_data = load_json("scenarios/sample_metrics.json")

    if args.fail:
        simulate_failure(metrics_data, args.fail)

    initial_health = {}
    for service in dependency_graph.keys():
        metrics = metrics_data.get(service, {})
        initial_health[service] = evaluate_health(metrics).value

    final_health = propagate_failures(dependency_graph, initial_health)

    roots = find_root_causes(dependency_graph, final_health)
    critical_paths = find_critical_paths(dependency_graph, roots)

    impact_scores = calculate_impact_scores(final_health)
    ranked = rank_services_by_impact(impact_scores)

    print("\nRoot Cause Services")
    print("-" * 30)
    for r in roots:
        print(f"- {r}")

    print("\nCritical Failure Paths")
    print("-" * 30)
    for root, branches in critical_paths.items():
        for branch in branches:
            print(f"{root}: {' -> '.join(branch)}")

    print("\nImpact Ranking (Most Dangerous First)")
    print("-" * 40)
    for service, score in ranked:
        print(f"{service:30} -> Impact Score {score}")


if __name__ == "__main__":
    main()
