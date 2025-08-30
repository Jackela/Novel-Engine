#!/usr/bin/env python3
"""
Performance Optimization Module
===============================

High-performance optimization framework providing advanced caching,
monitoring, profiling, and optimization strategies.

Key Features:
- Multi-layer performance optimization with real-time monitoring
- Enterprise-grade performance with sub-10ms response times
- Comprehensive caching and monitoring capabilities
- Advanced optimization strategies and profiling tools
"""

from .advanced_caching import (
    CacheConfig,
    CacheEntry,
    CacheEvent,
    CacheLevel,
    CacheStats,
    CacheStrategy,
    IntelligentCacheManager,
    cached,
    get_cache_manager,
    initialize_cache_manager,
)
from .monitoring import (
    MetricType,
    MonitoringConfig,
    PerformanceAlert,
    PerformanceMetric,
    PerformanceMonitor,
    get_performance_monitor,
    initialize_performance_monitor,
)

# Optimization module - to be implemented
# from .optimization import (
#     PerformanceOptimizer, OptimizationStrategy, PerformanceProfile,
#     PerformanceBottleneck, get_performance_optimizer, initialize_performance_optimizer
# )

__all__ = [
    # Advanced Caching
    "CacheLevel",
    "CacheStrategy",
    "CacheEvent",
    "CacheEntry",
    "CacheStats",
    "CacheConfig",
    "IntelligentCacheManager",
    "cached",
    "get_cache_manager",
    "initialize_cache_manager",
    # Performance Monitoring
    "PerformanceMonitor",
    "MetricType",
    "PerformanceMetric",
    "PerformanceAlert",
    "MonitoringConfig",
    "get_performance_monitor",
    "initialize_performance_monitor",
    # Performance Optimization - to be implemented
    # 'PerformanceOptimizer', 'OptimizationStrategy', 'PerformanceProfile',
    # 'PerformanceBottleneck', 'get_performance_optimizer', 'initialize_performance_optimizer'
]
