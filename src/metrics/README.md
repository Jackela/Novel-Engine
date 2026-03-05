# Metrics Module

## Purpose
Collects and reports application metrics for monitoring and observability. Provides insights into cache performance, cost savings, and system efficiency.

This module implements a metrics collection pattern that can publish to various backends (Prometheus, StatsD, CloudWatch) while providing a simple in-memory implementation for testing and development.

## Components

### MetricsPublisher (Abstract Interface)
Base interface for all metrics implementations.

```python
from src.metrics import MetricsPublisher

class MyMetrics(MetricsPublisher):
    def record_hit(self, kind: str) -> None:
        ...
    
    def record_eviction(self, count: int = 1) -> None:
        ...
    
    def record_invalidation(self, count: int = 1) -> None:
        ...
    
    def record_single_flight_merged(self, count: int = 1) -> None:
        ...
    
    def record_replay_hit(self, count: int = 1) -> None:
        ...
    
    def record_savings(self, tokens: int, cost: float) -> None:
        ...
    
    def set_cache_size(self, size: int) -> None:
        ...
    
    def snapshot(self) -> MetricsSnapshot:
        ...
```

### MetricsSnapshot
Data class containing point-in-time metrics.

**Attributes:**
- `ts`: Timestamp (ISO format)
- `cache_exact_hits`: Exact match cache hits
- `cache_semantic_hits`: Semantic similarity cache hits
- `cache_tool_hits`: Tool call cache hits
- `cache_size`: Current cache entry count
- `evictions`: Items evicted from cache
- `invalidations`: Cache invalidations
- `single_flight_merged`: Requests merged via single-flight
- `replay_hits`: Replay cache hits
- `saved_tokens`: Tokens saved through caching
- `saved_cost`: Cost savings in currency units

### InMemoryMetrics
In-memory metrics implementation for development and testing.

**File:** `src/metrics/inmemory.py`

```python
from src.metrics import InMemoryMetrics

metrics = InMemoryMetrics()

# Record cache hits
metrics.record_hit("exact")
metrics.record_hit("semantic")
metrics.record_hit("tool")

# Record savings
metrics.record_savings(tokens=150, cost=0.003)

# Update cache size
metrics.set_cache_size(100)

# Get snapshot
snapshot = metrics.snapshot()
print(f"Cache hits: {snapshot.cache_exact_hits}")
print(f"Cost saved: ${snapshot.saved_cost:.4f}")
```

### Global Metrics
Global metrics instance for application-wide use.

**File:** `src/metrics/global_metrics.py`

```python
from src.metrics.global_metrics import get_metrics

metrics = get_metrics()
metrics.record_hit("exact")
```

## Metrics Types

### Cache Performance
- **Exact Hits**: Identical prompt/response cached
- **Semantic Hits**: Similar meaning, different wording
- **Tool Hits**: Tool call results cached
- **Evictions**: Cache capacity management
- **Invalidations**: Stale data removal

### Cost Savings
- **Saved Tokens**: Tokens not sent to LLM due to cache
- **Saved Cost**: Monetary value of tokens saved

### Request Optimization
- **Single-Flight Merged**: Duplicate requests deduplicated
- **Replay Hits**: Replayed responses from cache

## Usage Examples

### Basic Recording
```python
from src.metrics import InMemoryMetrics

metrics = InMemoryMetrics()

# Cache operations
if cache_hit:
    metrics.record_hit("exact")
else:
    # Fetch from LLM
    response = llm.generate(prompt)
    cache.store(prompt, response)

# Cost tracking
tokens_used = response.token_count
cost = calculate_cost(tokens_used)
metrics.record_savings(tokens=tokens_used, cost=cost)

# Get current snapshot
snapshot = metrics.snapshot()
```

### Integration with AI Context
```python
from src.metrics import MetricsPublisher
from src.contexts.ai import ExecuteLLMService

class MetricsDecorator:
    def __init__(self, metrics: MetricsPublisher, service: ExecuteLLMService):
        self.metrics = metrics
        self.service = service
    
    async def execute(self, request):
        if request.cache_hit:
            self.metrics.record_hit("exact")
            self.metrics.record_savings(
                tokens=request.estimated_tokens,
                cost=request.estimated_cost
            )
        return await self.service.execute_async(request)
```

## Testing

```bash
pytest tests/metrics/ -v
```

## Configuration

No external configuration required. The in-memory implementation is suitable for:
- Unit testing
- Development environments
- Single-instance deployments

For production, implement `MetricsPublisher` with your preferred backend:

```python
class PrometheusMetrics(MetricsPublisher):
    def __init__(self):
        self.cache_hits = Counter('llm_cache_hits_total', 'Cache hits', ['kind'])
        self.cost_savings = Counter('llm_cost_savings_total', 'Cost savings')
    
    def record_hit(self, kind: str) -> None:
        self.cache_hits.labels(kind=kind).inc()
    
    def record_savings(self, tokens: int, cost: float) -> None:
        self.cost_savings.inc(cost)
    
    # ... implement other methods
```

## Integration

This module is used by:
- AI Context (cache performance tracking)
- Knowledge Context (retrieval metrics)
- Orchestration Context (execution metrics)

## Future Enhancements

- Prometheus exporter implementation
- StatsD integration
- CloudWatch metrics support
- Distributed tracing correlation
- Metric aggregation across instances
