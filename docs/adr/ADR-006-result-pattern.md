# ADR-006: Result Pattern for Error Handling

**Status**: Accepted
**Date**: 2026-02-03
**Deciders**: Architecture Team

## Context

The Novel Engine backend requires consistent error handling across all service layers. Traditional exception-based approaches have several issues:

1. **Implicit Control Flow**: Exceptions bypass return types, making error paths invisible
2. **Unhandled Exceptions**: Crashes occur when exceptions aren't caught
3. **Lack of Type Safety**: Exception types aren't enforced in function signatures
4. **Poor Testing**: Error paths are often untested or untestable
5. **Unclear Recovery**: No indication if an error is recoverable

### Requirements

1. **Explicit Errors**: Function signatures must declare possible failures
2. **Type Safety**: Compiler must enforce error handling
3. **Recovery Information**: Errors should indicate if retry is possible
4. **Structured Error Data**: Machine-readable codes with human-readable messages
5. **Chainable Operations**: Support for functional composition patterns

## Decision

We will implement a **Result[T, E]** pattern for all service layer error handling. Services return `Result[T, E]` instead of raising exceptions. Routers unwrap Results and convert to appropriate HTTP status codes.

### Core Implementation

```python
# src/core/result.py

from dataclasses import dataclass
from typing import TypeVar, Generic, TYPE_CHECKING

T = TypeVar('T')  # Success type
E = TypeVar('E')  # Error type

@dataclass(frozen=True)
class Error:
    """Structured error with machine-readable code and human-readable message."""
    code: str                    # Machine-readable identifier
    message: str                 # Human-readable description
    recoverable: bool = True     # Can the operation be retried?
    details: dict[str, Any] | None = None  # Additional context

class _Ok(Generic[T]):
    """Success variant containing a value."""
    def __init__(self, value: T) -> None:
        object.__setattr__(self, '_value', value)

    @property
    def value(self) -> T:
        return self._value

    @property
    def is_ok(self) -> bool:
        return True

    @property
    def is_error(self) -> bool:
        return False

class _Error(Generic[E]):
    """Error variant containing an Error object."""
    def __init__(self, error: E) -> None:
        object.__setattr__(self, '_error', error)

    @property
    def error(self) -> E:
        return self._error

    @property
    def is_ok(self) -> bool:
        return False

    @property
    def is_error(self) -> bool:
        return True

# Type aliases for return types
ResultOk = _Ok[T]
ResultError = _Error[Error]

# Factory functions
def Ok(value: T) -> ResultOk[T]:
    """Create a success Result."""
    return _Ok(value)

def Err(error: Error | str) -> ResultError[Error]:
    """Create an error Result. Accepts Error object or message string."""
    if isinstance(error, str):
        error = Error(code="UNKNOWN_ERROR", message=error)
    return _Error(error)
```

### Built-in Error Types

```python
# Common error constructors
def NotFoundError(message: str, details: dict | None = None) -> Error:
    return Error(code="NOT_FOUND", message=message, recoverable=False, details=details)

def ValidationError(message: str, details: dict | None = None) -> Error:
    return Error(code="VALIDATION_ERROR", message=message, recoverable=True, details=details)

def ConflictError(message: str, details: dict | None = None) -> Error:
    return Error(code="CONFLICT", message=message, recoverable=True, details=details)

def PermissionError(message: str, details: dict | None = None) -> Error:
    return Error(code="PERMISSION_DENIED", message=message, recoverable=False, details=details)

def ServiceUnavailableError(message: str, details: dict | None = None) -> Error:
    return Error(code="SERVICE_UNAVAILABLE", message=message, recoverable=True, details=details)
```

### Functional Composition

```python
# Methods on Result (planned extension)
class Result(Generic[T, E]):
    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform success value, pass through errors."""
        if self.is_ok:
            return Ok(fn(self.value))
        return self

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain operations that return Results."""
        if self.is_ok:
            return fn(self.value)
        return self

    def or_else(self, fn: Callable[[E], Result[T, F]]) -> Result[T, F]:
        """Recover from errors with a fallback Result."""
        if self.is_error:
            return fn(self.error)
        return self

    def on_success(self, fn: Callable[[T], None]) -> None:
        """Execute side effect on success."""
        if self.is_ok:
            fn(self.value)

    def on_error(self, fn: Callable[[E], None]) -> None:
        """Execute side effect on error."""
        if self.is_error:
            fn(self.error)
```

### Service Layer Usage

```python
# src/contexts/character/application/services/character_application_service.py

from src.core.result import Ok, Err, NotFoundError, ConflictError, ResultOk, ResultError

class CharacterApplicationService:
    def __init__(self, repository: CharacterRepository):
        self.repository = repository

    async def create_character(
        self,
        character_name: str,
        tenant_id: str,
    ) -> ResultOk[CharacterID] | ResultError[Error]:
        """
        Create a new character.

        Why: Returns Result to make error handling explicit and type-safe.
        """
        # Check for name conflict
        existing = await self.repository.find_by_name(character_name, tenant_id)
        if existing:
            return Err(ConflictError(
                message=f"Character '{character_name}' already exists",
                details={"character_name": character_name, "tenant_id": tenant_id},
            ))

        # Create character
        character_id = CharacterID.generate()
        character = Character(
            id=character_id,
            name=character_name,
            tenant_id=tenant_id,
            # ... other fields
        )

        await self.repository.save(character)
        return Ok(character_id)

    async def get_character(
        self,
        character_id: CharacterID,
        tenant_id: str,
    ) -> ResultOk[Character] | ResultError[Error]:
        """Get a character by ID."""
        character = await self.repository.find_by_id(character_id, tenant_id)
        if not character:
            return Err(NotFoundError(
                message=f"Character '{character_id}' not found",
                details={"character_id": str(character_id), "tenant_id": tenant_id},
            ))
        return Ok(character)
```

### Router Integration

```python
# src/api/routers/characters.py

from fastapi import HTTPException, status
from src.core.result import ResultOk, ResultError

@router.get("/characters/{character_id}")
async def get_character(
    character_id: str,
    tenant_id: str,
) -> CharacterResponse:
    """Get a character by ID."""
    result: ResultOk[Character] | ResultError[Error] = await service.get_character(
        CharacterID(character_id),
        tenant_id,
    )

    if result.is_error:
        error: Error = result.error
        status_code = _error_code_to_status(error.code)
        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message},
        )

    return CharacterResponse(data=result.value)

def _error_code_to_status(code: str) -> int:
    """Map error codes to HTTP status codes."""
    return {
        "NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "CONFLICT": status.HTTP_409_CONFLICT,
        "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
        "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
    }.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)
```

## Alternatives Considered

### 1. **Exception-Based Handling**

Traditional Python approach with try/except blocks.

**Pros**:
- Pythonic and familiar
- Built-in language support
- Minimal boilerplate

**Cons**:
- Implicit control flow (errors invisible in signatures)
- No compiler enforcement
- Easy to forget to handle
- Stack traces for expected failures
- No recovery information

**Rejected for**: Result pattern provides explicit, type-safe error handling.

### 2. **Typed Exceptions**

Define specific exception classes with structured data.

**Pros**:
- Still Pythonic
- Can add structured data to exceptions
- Type checkers can recognize raised types

**Cons**:
- Still implicit in function signatures
- Requires try/except at every call site
- No indication of recoverability
- Stack traces for expected errors

**Rejected for**: Still suffers from implicit control flow issues.

### 3. **Status Object Pattern**

Return objects with status enum and optional data.

**Pros**:
- Explicit in return type
- Simple to understand

**Cons**:
- Less type-safe (no generic error type)
- No functional composition
- Requires field access checks
- Verbose call sites

**Rejected for**: Result variant pattern provides better type safety and ergonomics.

### 4. **Maybe/Option Pattern**

Return None or optional values for failures.

**Pros**:
- Simple for "not found" cases
- Familiar from other languages

**Cons**:
- No error context (why did it fail?)
- No distinction between error types
- No recovery information
- Limited to binary success/failure

**Rejected for**: Need rich error information beyond "not found".

## Consequences

### Positive

1. **Explicit Errors**: Function signatures declare possible failures
2. **Type Safety**: Mypy enforces Result unwrapping
3. **Testable**: Both success and error paths are easily testable
4. **Structured Data**: Machine-readable codes with context
5. **Recovery Info**: `recoverable` flag indicates retry eligibility
6. **Chainable**: Functional methods enable clean composition
7. **No Stack Leaks**: Expected errors don't produce stack traces
8. **Clear Intent**: `Ok()` and `Err()` make success/failure explicit

### Negative

1. **Migration Effort**: Existing code must be refactored
2. **Verbosity**: More boilerplate than raising exceptions
3. **Learning Curve**: Team must learn Result pattern
4. **Router Complexity**: Need to unwrap Results at API boundaries
5. **Ecosystem**: Some libraries don't support Result pattern

### Risks and Mitigation

**Risk**: Team forgets to check `.is_error` before accessing `.value`
**Mitigation**: Mypy catches this; code review enforces pattern

**Risk**: Inconsistent Result usage across codebase
**Mitigation**: CIT-003 implemented pattern in reference services; integration tests enforce (CIT-010)

**Risk**: Performance overhead of Result objects
**Mitigation**: Negligible compared to database/LLM calls; micro-optimization not needed

**Risk**: Third-party libraries still raise exceptions
**Mitigation**: Wrap external calls in try/except and convert to Results at boundaries

## Migration Guide

### Step 1: Update Service Signature

```python
# Before
async def get_character(self, id: str) -> Character:
    ...

# After
async def get_character(self, id: str) -> ResultOk[Character] | ResultError[Error]:
    ...
```

### Step 2: Replace Raises with Returns

```python
# Before
if not character:
    raise ValueError("Character not found")

# After
if not character:
    return Err(NotFoundError("Character not found"))
```

### Step 3: Update Router Endpoints

```python
# Before
character = await service.get_character(id)
return CharacterResponse(data=character)

# After
result = await service.get_character(id)
if result.is_error:
    # Convert to HTTP response
return CharacterResponse(data=result.value)
```

### Step 4: Update Tests

```python
# Before
def test_get_character_not_found(self):
    with pytest.raises(ValueError):
        service.get_character("invalid-id")

# After
def test_get_character_not_found(self):
    result = await service.get_character("invalid-id")
    assert result.is_error
    assert result.error.code == "NOT_FOUND"
```

## Testing Patterns

```python
# Unit tests for Result returns
@pytest.mark.unit
async def test_create_character_returns_result_on_success():
    service = CharacterApplicationService(mock_repository)
    result = await service.create_character("Alice", "tenant-1")

    assert result.is_ok
    assert isinstance(result.value, CharacterID)

@pytest.mark.unit
async def test_create_character_returns_error_on_duplicate():
    mock_repository.find_by_name.return_value = existing_character
    service = CharacterApplicationService(mock_repository)
    result = await service.create_character("Alice", "tenant-1")

    assert result.is_error
    assert result.error.code == "CONFLICT"
    assert result.error.recoverable is True

# Integration tests for router mapping
@pytest.mark.integration
async def test_get_character_maps_404_on_not_found(client):
    response = await client.get("/api/characters/invalid-id")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"
```

## Implementation Notes

### Error Code Design

| Code | HTTP Status | Recoverable | Usage |
|------|-------------|-------------|-------|
| `NOT_FOUND` | 404 | No | Entity doesn't exist |
| `VALIDATION_ERROR` | 400 | Yes | Invalid input data |
| `CONFLICT` | 409 | Yes | State conflict (duplicate, version mismatch) |
| `PERMISSION_DENIED` | 403 | No | User lacks authorization |
| `SERVICE_UNAVAILABLE` | 503 | Yes | External service down |
| `INVALID_REQUEST` | 400 | Yes | Malformed request |
| `INTERNAL_ERROR` | 500 | No | Unexpected failures |

### Layer Responsibilities

| Layer | Responsibility | Pattern |
|-------|----------------|---------|
| **Domain** | Business rule validation | Return domain-specific Errors |
| **Services** | Orchestration errors | Return Result with Error |
| **Routers** | HTTP translation | Convert Result → status codes |
| **Repositories** | Data access failures | Return Result or raise repository-specific exceptions |

### Current Implementation Status

- ✅ Core `Result[T, E]` implementation in `src/core/result.py`
- ✅ Reference implementations in:
  - `orchestration_service.py`
  - `character_application_service.py`
  - `pacing_service.py`
- ✅ Router integration in `orchestration.py`
- ✅ Documentation in `docs/architecture/error-handling.md`
- 🚧 Integration tests (planned in CIT-010)

## Related Decisions

- CIT-003: Result Pattern Implementation (core implementation)
- CIT-010: Integration Test Coverage (Result pattern tests)
- ADR-003: Pydantic Schema Architecture

## Status Changes

- 2026-02-03: Proposed and accepted as part of Code Citadel documentation effort
