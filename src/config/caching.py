from dataclasses import dataclass


@dataclass
class CachingConfig:
    enable_exact_cache: bool = True
    enable_semantic_cache: bool = True
    enable_single_flight: bool = True
    semantic_threshold_high: float = 0.92
    semantic_threshold_low: float = 0.85
    semantic_guard_keyword_overlap: float = 0.40
    semantic_guard_length_delta_pct: float = 0.15
    semantic_ttl_hours: int = 24


default_caching_config = CachingConfig()
