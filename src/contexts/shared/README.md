# Shared Context

## Overview
The Shared Context contains cross-cutting concerns and shared infrastructure used by all other contexts in the Novel Engine platform. It provides common utilities, base classes, and infrastructure components that don't belong to any specific domain.

This context is intentionally lightweight and focuses on technical concerns rather than business logic. It enables code reuse and consistency across the platform.

## Domain

### Aggregates
- **None**: This context contains no domain aggregates.

### Entities
- **None**: No domain entities.

### Value Objects
- **Result**: Operation result wrapper (Ok/Err pattern)
  - Success/failure indication
  - Error details on failure
  - Chaining support
  
- **EntityId**: Base identifier with UUID support
- **Timestamp**: UTC timestamp handling

### Domain Events
- **None**: No domain events.

## Application

### Services
- **None**: No application services.

### Commands
- **None**: No commands.

### Queries
- **None**: No queries.

## Infrastructure

### Components
- **EventBus**: Enterprise event bus
  - Publish/subscribe pattern
  - Async event handling
  - Priority levels
  
- **Result Types**: Error handling primitives
  - `SaveError`: Persistence failures
  - `ValidationError`: Input validation failures
  
- **Base Classes**: Common infrastructure
  - `Entity`: Base entity class
  - `ValueObject`: Base value object
  - `Event`: Base domain event

### External Services
- None

## API
- None directly exposed

## Testing

### Running Tests
```bash
# Unit tests
pytest tests/contexts/shared/unit/ -v

# All context tests
pytest tests/contexts/shared/ -v
```

### Test Coverage
Current coverage: N/A
Target coverage: 80%

## Architecture Decision Records
- ADR-001: Result pattern for explicit error handling
- ADR-002: EventBus for decoupled communication

## Integration Points

### Inbound
- None (shared utility context)

### Outbound
- None

### Dependencies
- **Domain**: None
- **Application**: None
- **Infrastructure**: None (base layer)

## Development Guide

### Adding New Features
1. Add shared utilities here only if used by 3+ contexts
2. Prefer keeping domain logic in specific contexts
3. Maintain backward compatibility for shared types

## Maintainer
Team: @platform-team
Contact: platform@example.com
