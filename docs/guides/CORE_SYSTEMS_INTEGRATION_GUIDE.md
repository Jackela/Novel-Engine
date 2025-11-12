# Core Systems Integration Guide
==================================

## Quick Integration Checklist

### 1. Import Core Systems
```python
from src.core.error_handler import (
    CentralizedErrorHandler, ErrorContext, ErrorSeverity, 
    ErrorCategory, RecoveryStrategy, get_error_handler, handle_error
)
from src.core.logging_system import (
    StructuredLogger, LogLevel, LogCategory, LogContext, 
    get_logger, with_context, PerformanceTracker
)
```

### 2. Initialize in Component __init__
```python
# Initialize core systems
self.logger = get_logger(f"{self.__class__.__name__}_{id(self)}")
self.error_handler = get_error_handler()

# Create logging context
self.log_context = LogContext(
    component=self.__class__.__name__,
    session_id=getattr(self, 'session_id', None),
    metadata={'component_id': id(self)}
)
```

### 3. Replace Standard Logging
```python
# Before
logging.info("Operation started")

# After
self.logger.info("Operation started", context=self.log_context)
```

### 4. Add Error Handling
```python
try:
    result = await risky_operation()
except Exception as e:
    error_record = await handle_error(
        error=e,
        component=self.__class__.__name__,
        operation="risky_operation"
    )
    # Handle error record as needed
```

### 5. Performance Tracking
```python
with self.logger.track_performance("operation_name") as tracker:
    result = await long_running_operation()
    tracker.add_metric("items_processed", len(result))
```

## Integration Priority

1. **HIGH**: PersonaCore, DirectorAgent components ✅
2. **MEDIUM**: Enhanced Bridge, DialogueManager ✅
3. **LOW**: Utility components, type definitions

## Validation

Run `python test_core_systems.py` to validate integration.
