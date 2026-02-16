# Error Handling Architecture

## Overview

This document describes the Novel Engine's error handling strategy using the **Result pattern** for explicit, type-safe error management without exceptions.

## Why Result[T, E] Pattern?

### Problems with Exceptions

1. **Implicit control flow**: Exceptions bypass normal return paths, making code harder to follow
2. **Unhandled errors**: Exceptions can crash processes if not caught
3. **Type safety**: Function signatures don't declare what errors they might throw
4. **Debugging difficulty**: Stack traces hide the business logic path

### Benefits of Result Pattern

1. **Explicit errors**: Return type `Result[T, E]` clearly shows possible failures
2. **Type safe**: Compilers/type checkers ensure errors are handled
3. **Chainable**: Methods like `.map()`, `.and_then()` enable functional composition
4. **Testable**: Both success and failure paths are easily testable

## Result Type

### Basic Structure

```python
from src.core.result import Result, Ok, Err, Error

# A Result is either Ok(value) or Err(error)
Result[Character, Error]
```

### Creating Results

```python
from src.core.result import Ok, Err, NotFoundError, ValidationError

# Success case
def get_character(id: str) -> Result[Character, Error]:
    if char := repository.find(id):
        return Ok(char)
    return Err(NotFoundError(f"Character {id} not found"))

# Error with details
return Err(ValidationError(
    message="Name too short",
    field="name",
    details={"min_length": 3, "actual": 2}
))
```

### Accessing Values

```python
result = service.get_character("123")

# Check state
if result.is_ok:
    character = result.value
    print(f"Found: {character.name}")
else:
    error = result.error
    print(f"Error: {error.code} - {error.message}")

# Unwrap with default
character = result.unwrap(default=None)

# Unsafe unwrap (raises ValueError if error)
character = result.value  # only if is_ok == True
```

## Built-in Error Types

| Error Type | Code | Recoverable | Usage |
|------------|------|-------------|-------|
| `Error` | (custom) | True | Generic errors |
| `NotFoundError` | `NOT_FOUND` | False | Entity not found |
| `ValidationError` | `VALIDATION_ERROR` | True | Input validation failed |
| `ConflictError` | `CONFLICT` | True | State conflict (e.g., duplicate name) |
| `PermissionError` | `PERMISSION_DENIED` | False | Authorization failed |

### Error Structure

```python
@dataclass(frozen=True)
class Error:
    code: str              # Machine-readable identifier
    message: str           # Human-readable description
    recoverable: bool = True  # Can the operation be retried?
    details: dict[str, Any] | None = None  # Additional context
```

## Functional Composition

### map(): Transform Values

```python
result: Result[Character, Error] = service.get_character("123")

# Transform the value if Ok, pass through error if Err
name_result: Result[str, Error] = result.map(lambda char: char.name)

# Chaining
formatted = result.map(lambda char: char.name).map(str.upper)
```

### and_then(): Chain Results

```python
def validate_character(char: Character) -> Result[Character, Error]:
    if not char.is_valid:
        return Err(ValidationError("Invalid character"))
    return Ok(char)

# Chain operations - short-circuits on first error
result = (service.get_character("123")
          .and_then(validate_character)
          .and_then(lambda c: service.save_character(c)))
```

### or_else(): Fallback on Error

```python
# Try primary, fall back to cache on error
def get_character(id: str) -> Result[Character, Error]:
    return (service.get_from_db(id)
            .or_else(lambda e: cache.get(id)
                    if e.code == "NOT_FOUND" else Err(e)))
```

### Side Effects: on_success(), on_error()

```python
result = service.get_character("123")
result.on_success(lambda c: logger.info(f"Found {c.name}"))
result.on_error(lambda e: logger.warning(f"Failed: {e.message}"))
```

## Service Layer Usage

### Before (Exception-based)

```python
async def create_character(self, name: str) -> CharacterID:
    existing = await self.repository.find_by_name(name)
    if existing:
        raise ValueError(f"Character '{name}' already taken")

    character_id = await self.repository.create(name)
    return character_id
```

### After (Result Pattern)

```python
async def create_character(self, name: str) -> Result[CharacterID, Error]:
    existing = await self.repository.find_by_name(name)
    if existing:
        return Err(ConflictError(
            message=f"Character '{name}' already taken",
            details={"name": name}
        ))

    character_id = await self.repository.create(name)
    return Ok(character_id)
```

## Router Layer Usage

Routers unwrap Results and convert to appropriate HTTP status codes:

```python
from fastapi import APIRouter, HTTPException, status
from src.core.result import Result, Error

@router.get("/characters/{id}")
async def get_character(id: str) -> CharacterResponse:
    result: Result = await service.get_character(id)

    if result.is_error:
        error: Error = result.error
        status_code = {
            "NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
            "PERMISSION_DENIED": status.HTTP_403_FORBIDDEN,
        }.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        raise HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.message}
        )

    return CharacterResponse(success=True, data=result.value)
```

## HTTP Status Code Mapping

| Error Code | HTTP Status | Reason |
|------------|-------------|--------|
| `NOT_FOUND` | 404 | Resource doesn't exist |
| `VALIDATION_ERROR` | 400 | Invalid input |
| `CONFLICT` | 409 | State conflict |
| `PERMISSION_DENIED` | 403 | Not authorized |
| `SERVICE_UNAVAILABLE` | 503 | Downstream dependency issue |
| Other errors | 500 | Internal server error |

## Migration Guide

### Step 1: Update Service Methods

Change method signatures to return `Result[T, Error]`:

```python
# Before
async def get_character(self, id: str) -> Character:
    ...

# After
async def get_character(self, id: str) -> Result[Character, Error]:
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
    # Handle error
return CharacterResponse(data=result.value)
```

## Testing

### Testing Success Paths

```python
async def test_get_character_returns_ok():
    result = await service.get_character("123")
    assert result.is_ok
    assert result.value.name == "Alice"
```

### Testing Error Paths

```python
async def test_get_character_returns_error():
    result = await service.get_character("nonexistent")
    assert result.is_error
    assert result.error.code == "NOT_FOUND"
```

### Testing Chains

```python
async def test_character_validation_chain():
    result = (service.get_character("123")
              .and_then(validate_character)
              .and_then(save_character))
    assert result.is_ok
```

## Best Practices

1. **Be specific with error types**: Use `NotFoundError`, `ValidationError`, etc. instead of generic `Error`
2. **Include details**: Add relevant context to `details` dict for debugging
3. **Mark recoverable correctly**: Set `recoverable=False` for errors that shouldn't be retried
4. **Handle at layer boundaries**: Convert domain errors to HTTP responses in routers only
5. **Log before returning**: Use `.on_error()` for logging when unwrapping in routers
6. **Don't swallow errors**: Every `Err` should eventually be handled or propagated

## Anti-Patterns to Avoid

```python
# DON'T: Unwrap without checking
character = result.value  # Crashes if result is Err

# DON'T: Convert Result back to exceptions
if result.is_error:
    raise Exception(result.error)  # Defeats the purpose

# DON'T: Return None for errors
return None  # Use Err(Error(...)) instead

# DON'T: Mix exceptions and Results
def bad(): Result[T, E]:
    raise ValueError("Inconsistent!")
```

## References

- Implementation: `src/core/result.py`
- Example usage: `src/api/services/orchestration_service.py`
- Example router: `src/api/routers/orchestration.py`
- Related ADR: `docs/adr/ADR-006-result-pattern.md` (to be created)
