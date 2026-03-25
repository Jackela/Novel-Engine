# Circuit Breaker and Fallback Documentation

## Overview

Novel Engine now includes comprehensive circuit breaker and fallback strategies to ensure production-ready resilience. This protects against cascading failures when external services (OpenAI API, Honcho, Database) become unavailable.

## Features

### 1. Circuit Breaker Protection

All external service calls are protected by circuit breakers with configurable thresholds:

- **OpenAI API**: 3 failures before opening, 60s recovery timeout
- **Honcho API**: 5 failures before opening, 30s recovery timeout
- **Database**: 10 failures before opening, 30s recovery timeout
- **External Services**: 5 failures before opening, 45s recovery timeout

### 2. Fallback Strategies

When services fail, the system uses intelligent fallback strategies:

- **CachedFallback**: Returns previously cached embeddings
- **StaticFallback**: Returns zero embeddings (maintains system availability)
- **AlternativeServiceFallback**: Tries backup embedding providers
- **RetryWithFallback**: Retries with exponential backoff before falling back

### 3. Health Monitoring

Circuit breaker states are exposed through the health check endpoint:

```python
GET /health

{
  "overall_status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "components": {
    "circuit_breakers": {
      "status": "healthy",
      "message": "All circuits closed",
      "circuits": {
        "openai_api": {
          "name": "openai_api",
          "state": "closed",
          "failure_count": 0,
          "success_count": 0
        }
      }
    }
  }
}
```

## Usage

### Using Resilient Embedding Service

The `ResilientEmbeddingService` automatically wraps your embedding service with circuit breaker protection:

```python
from src.contexts.knowledge.infrastructure.services.resilient_embedding_service import (
    ResilientEmbeddingService,
)
from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
    OpenAIEmbeddingService,
)

# Create base service
base_service = OpenAIEmbeddingService(api_key="your-key")

# Wrap with resilience
cache = {}
resilient_service = ResilientEmbeddingService(
    primary_service=base_service,
    cache=cache,
    circuit_breaker_name="openai_api",
    fallback_to_zero=True,
)

# Use normally - circuit breaker handles failures automatically
embedding = await resilient_service.embed("Your text here")
```

### Manual Circuit Breaker Usage

For other services, use the circuit breaker directly:

```python
from src.shared.infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
)

# Get existing circuit breaker
cb = CircuitBreakerRegistry.get("openai_api")

# Or create and register new one
cb = CircuitBreaker(
    name="my_service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
    ),
)
CircuitBreakerRegistry.register("my_service", cb)

# Use circuit breaker
async def my_service_call():
    return await cb.call(external_api_function, arg1, arg2)
```

### Fallback Strategies

Use fallback strategies for graceful degradation:

```python
from src.shared.infrastructure.fallback import (
    StaticFallback,
    CachedFallback,
    RetryWithFallback,
)

# Static fallback
strategy = StaticFallback(fallback_value=[0.0] * 1536)
result = await strategy.execute(risky_function)

# Cached fallback
cache = {}
strategy = CachedFallback(cache, "cache_key", default_value=[0.0] * 1536)
result = await strategy.execute(risky_function)

# Retry with fallback
fallback = StaticFallback([0.0] * 1536)
strategy = RetryWithFallback(fallback, max_retries=3)
result = await strategy.execute(risky_function)
```

## Configuration

Circuit breaker settings can be configured via environment variables:

```bash
# Enable/disable circuit breakers
CIRCUIT_BREAKER_ENABLED=true

# OpenAI API settings
CIRCUIT_BREAKER_OPENAI_FAILURE_THRESHOLD=3
CIRCUIT_BREAKER_OPENAI_RECOVERY_TIMEOUT=60.0

# Embedding service fallback
CIRCUIT_BREAKER_EMBEDDING_FALLBACK_TO_ZERO=true
CIRCUIT_BREAKER_EMBEDDING_ENABLE_CACHE=true

# Retry settings
CIRCUIT_BREAKER_RETRY_MAX_ATTEMPTS=3
CIRCUIT_BREAKER_RETRY_BASE_DELAY=1.0
```

Or via YAML configuration:

```yaml
circuit_breaker:
  enabled: true
  openai_failure_threshold: 3
  openai_recovery_timeout: 60.0
  honcho_failure_threshold: 5
  honcho_recovery_timeout: 30.0
  embedding_fallback_to_zero: true
  embedding_enable_cache: true
  retry_max_attempts: 3
  retry_base_delay: 1.0
```

## Monitoring

### Health Check Integration

Circuit breaker health is automatically included in the health check endpoint. Monitor for:

- **healthy**: All circuits closed, system operating normally
- **degraded**: Some circuits are open or half-open, reduced functionality
- **unhealthy**: Critical circuits are open, system may be unavailable

### Metrics

Each circuit breaker exposes metrics:

```python
from src.shared.infrastructure.circuit_breaker import CircuitBreakerRegistry

# Get all circuit breaker states
states = CircuitBreakerRegistry.get_all_states()
for name, metrics in states.items():
    print(f"{name}: {metrics['state']} (failures: {metrics['failure_count']})")
```

### Manual Reset

For emergency recovery or testing:

```python
from src.shared.infrastructure.circuit_breaker import CircuitBreakerRegistry

# Reset specific circuit breaker
cb = CircuitBreakerRegistry.get("openai_api")
cb.reset()

# Reset all circuit breakers
CircuitBreakerRegistry.reset_all()
```

## Testing

Run the circuit breaker tests:

```bash
# Run all circuit breaker tests
pytest tests/shared/infrastructure/circuit_breaker/ -v

# Run with coverage
pytest tests/shared/infrastructure/circuit_breaker/ --cov=src.shared.infrastructure.circuit_breaker -v
```

## Architecture

### Circuit States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Service failing, requests rejected immediately
3. **HALF_OPEN**: Testing if service recovered, limited requests allowed

### State Transitions

```
CLOSED → (threshold failures) → OPEN
OPEN → (timeout expires) → HALF_OPEN
HALF_OPEN → (success threshold) → CLOSED
HALF_OPEN → (any failure) → OPEN
```

### Fallback Chain

```
Primary Service
    ↓ (failure)
Circuit Breaker Check
    ↓ (if open)
Cached Value
    ↓ (if no cache)
Zero Embeddings (or configured fallback)
```

## Best Practices

1. **Always use resilient embedding service** for production deployments
2. **Monitor health checks** to detect circuit breaker state changes
3. **Configure appropriate thresholds** based on your SLA requirements
4. **Use caching** for embedding fallbacks to maintain search quality
5. **Set up alerts** for when circuits open
6. **Test failure scenarios** in staging environments

## Troubleshooting

### Circuit breaker opens too quickly

Increase the failure threshold:
```python
config.failure_threshold = 10  # Default: 3 for OpenAI
```

### Recovery takes too long

Reduce the recovery timeout:
```python
config.recovery_timeout = 30.0  # Default: 60.0 for OpenAI
```

### Fallback returns zero embeddings

Check `fallback_to_zero` setting. If you need actual embeddings even during outages:
- Enable caching to serve stale embeddings
- Configure alternative embedding providers
- Increase retry attempts

## Migration Guide

### From Direct OpenAI Service

Before:
```python
from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
    OpenAIEmbeddingService,
)

embedding_service = OpenAIEmbeddingService(api_key="key")
```

After:
```python
# DI Container automatically wraps with ResilientEmbeddingService
# Or manually:
from src.contexts.knowledge.infrastructure.services.resilient_embedding_service import (
    ResilientEmbeddingService,
)
from src.contexts.knowledge.infrastructure.services.openai_embedding_service import (
    OpenAIEmbeddingService,
)

base_service = OpenAIEmbeddingService(api_key="key")
embedding_service = ResilientEmbeddingService(
    primary_service=base_service,
    fallback_to_zero=True,
)
```

The interface remains the same - just use `embedding_service.embed()` as before.
