#!/usr/bin/env python3
from pydantic import BaseModel, Field, field_validator
from typing import List

class TestModel(BaseModel):
    participants: List[str] = Field(..., min_length=1)
    
    @field_validator('participants')
    @classmethod
    def validate_participants(cls, v):
        print(f'Validator called with: {v}')
        if not v or len(v) == 0:
            raise ValueError('At least one participant is required')
        return v

# Test 1: Empty list
print("Test 1: Empty list")
try:
    m = TestModel(participants=[])
    print(f'  SUCCESS: Created model with empty list: {m}')
except Exception as e:
    print(f'  FAILED: {type(e).__name__}: {e}')

# Test 2: Valid list
print("\nTest 2: Valid list")
try:
    m = TestModel(participants=['test'])
    print(f'  SUCCESS: Created model: {m}')
except Exception as e:
    print(f'  FAILED: {type(e).__name__}: {e}')

# Test 3: Check if min_length on Field applies to list or string items
class TestModel2(BaseModel):
    participants: List[str] = Field(..., min_length=1, description="Test field")

print("\nTest 3: Field(min_length=1) without custom validator")
try:
    m = TestModel2(participants=[])
    print(f'  SUCCESS: Created model with empty list: {m}')
except Exception as e:
    print(f'  FAILED: {type(e).__name__}: {e}')

try:
    m = TestModel2(participants=[''])
    print(f'  SUCCESS: Created model with empty string: {m}')
except Exception as e:
    print(f'  FAILED: {type(e).__name__}: {e}')
