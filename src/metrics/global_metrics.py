"""Global singleton metrics instance.

Provides a module-level singleton for application-wide metrics collection.
Import this module to record metrics from any part of the codebase.

Example:
    >>> from src.metrics.global_metrics import metrics
    >>> metrics.record_hit("exact")
    >>> snapshot = metrics.snapshot()
"""

from src.metrics.inmemory import InMemoryMetrics

# Global singleton metrics publisher for cache/coordinator reporting
metrics = InMemoryMetrics()
