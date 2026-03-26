"""
Token Tracker Configuration

Configuration classes for the token tracking system.
"""

from dataclasses import dataclass


@dataclass
class TokenTrackerConfig:
    """
    Configuration for TokenTracker.

    Attributes:
        enabled: Whether tracking is enabled
        count_input_tokens: Whether to count input tokens when not provided
        estimate_missing_tokens: Whether to estimate tokens when API doesn't return them
        batch_size: Number of records to batch before saving
        flush_interval_seconds: Interval for auto-flushing batched records
        track_individual_calls: Track individual calls (vs. only aggregates)
    """

    enabled: bool = True
    count_input_tokens: bool = True
    estimate_missing_tokens: bool = True
    batch_size: int = 100
    flush_interval_seconds: float = 10.0
    track_individual_calls: bool = True


# Type alias for backward compatibility
TokenAwareConfig = TokenTrackerConfig
