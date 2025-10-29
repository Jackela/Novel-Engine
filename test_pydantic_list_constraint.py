#!/usr/bin/env python3
from pydantic import BaseModel, Field, ValidationError
from typing import List, Annotated

print("Pydantic v2 List Constraint Tests\n")

# Test 1: Field(min_length=1) on List[str]
class Model1(BaseModel):
    participants: List[str] = Field(..., min_length=1)

print("Test 1: Field(min_length=1) on List[str]")
try:
    m = Model1(participants=[])
    print(f"  FAIL: Accepted empty list")
except ValidationError as e:
    print(f"  PASS: Rejected empty list")
    print(f"  Error: {e.errors()[0]['type']}")

# Test 2: Using Annotated with constraints (Pydantic v2 recommended approach)
class Model2(BaseModel):
    participants: Annotated[List[str], Field(min_length=1)]

print("\nTest 2: Annotated[List[str], Field(min_length=1)]")
try:
    m = Model2(participants=[])
    print(f"  FAIL: Accepted empty list")
except ValidationError as e:
    print(f"  PASS: Rejected empty list")
    print(f"  Error: {e.errors()[0]['type']}")

# Test 3: Check if FastAPI would automatically handle this
from fastapi import FastAPI
from fastapi.testclient import TestClient

app = FastAPI()

@app.post("/test1")
async def test1(data: Model1):
    return {"success": True}

@app.post("/test2")
async def test2(data: Model2):
    return {"success": True}

client = TestClient(app)

print("\nTest 3: FastAPI automatic validation - Model1")
response = client.post("/test1", json={"participants": []})
print(f"  Status: {response.status_code}")
if response.status_code != 200:
    print(f"  Error: {response.json()}")

print("\nTest 4: FastAPI automatic validation - Model2")
response = client.post("/test2", json={"participants": []})
print(f"  Status: {response.status_code}")
if response.status_code != 200:
    print(f"  Error: {response.json()}")

print("\nTest 5: Check actual TurnExecutionRequest")
import sys
sys.path.insert(0, 'D:\\Code\\Novel-Engine')
from contexts.orchestration.api.turn_api import TurnExecutionRequest

try:
    req = TurnExecutionRequest(participants=[], async_execution=False)
    print(f"  FAIL: TurnExecutionRequest accepted empty list")
except ValidationError as e:
    print(f"  PASS: TurnExecutionRequest rejected empty list")
    print(f"  Errors: {[err['type'] for err in e.errors()]}")
