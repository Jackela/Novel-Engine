#!/usr/bin/env python3
import asyncio
import httpx
from contexts.orchestration.api.turn_api import app
from fastapi.testclient import TestClient

# Test with TestClient (synchronous)
client = TestClient(app)

print("Test 1: Empty participants with TestClient")
response = client.post(
    "/v1/turns:run",
    json={"participants": [], "async_execution": False}
)
print(f"  Status: {response.status_code}")
print(f"  Response: {response.json()}")

print("\nTest 2: Valid participants with TestClient")
response = client.post(
    "/v1/turns:run",
    json={"participants": ["test"], "async_execution": False}
)
print(f"  Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"  Response keys: {list(data.keys())}")
else:
    print(f"  Response: {response.json()}")
