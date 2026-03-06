"""Core Novel Engine infrastructure components."""

# Result Pattern Exports
from .result import (
    ConflictError,
    Err,
    Error,
    NotFoundError,
    Ok,
    PermissionError,
    Result,
    SaveError,
    Unwrap,
    ValidationError,
)
from .result_compat import (
    ResultMixin,
    catch_to_result,
    map_result_list,
    result_from_bool,
    result_from_optional,
    result_to_standard_response,
    standard_response_to_result,
    wrap_with_fallback,
)

__all__ = [
    # Result Pattern Core
    "Result",
    "Ok",
    "Err",
    "Unwrap",
    "Error",
    # Error Types
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "PermissionError",
    "SaveError",
    # Compatibility Helpers
    "ResultMixin",
    "result_to_standard_response",
    "standard_response_to_result",
    "result_from_optional",
    "result_from_bool",
    "catch_to_result",
    "map_result_list",
    "wrap_with_fallback",
]
