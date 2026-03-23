import argparse
import json
import os
from typing import Dict, List

import boto3


def load_graph(path: str) -> Dict[str, List[str]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed service_dependency_graph DynamoDB table")
    parser.add_argument("--graph", default="data/dependencyGraph.json", help="Path to dependencyGraph.json")
    parser.add_argument("--table", default=os.getenv("GRAPH_TABLE_NAME", "service_dependency_graph"), help="DynamoDB table name")
    parser.add_argument("--region", default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-south-1", help="AWS region")
    args = parser.parse_args()

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    table = dynamodb.Table(args.table)

    graph = load_graph(args.graph)

    # The Lambda expects items like:
    # { "service_name": "<svc>", "depends_on": ["downstream1", ...] }
    #
    # Your JSON is of shape:
    # { "service": ["dependencyA", "dependencyB"] }
    #
    # NOTE: In your repository JSON, the list looks more like "upstream prerequisites".
    # In your AWS table screenshot earlier, you used depends_on as downstream.
    # Pick ONE convention and keep it consistent.
    #
    # Here we seed exactly as your JSON expresses it:
    # service_name = key, depends_on = list value
    with table.batch_writer() as batch:
        for service_name, depends_on in graph.items():
            batch.put_item(Item={"service_name": service_name, "depends_on": depends_on})

    print(f"Seeded {len(graph)} services into {args.table} in region {args.region}")


if __name__ == "__main__":
    main()