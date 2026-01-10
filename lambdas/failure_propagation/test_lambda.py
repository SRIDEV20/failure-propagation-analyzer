from handler import lambda_handler
import json

with open("event_ingest.json") as f:
    event = json.load(f)

response = lambda_handler(event, None)
print(response)
