#!/usr/bin/env python3
"""
++ SACRED PERFORMANCE MODULE BLESSED BY THE OMNISSIAH ++
========================================================

High-performance optimization framework providing advanced caching,
monitoring, profiling, and optimization strategies.

++ THROUGH DIVINE OPTIMIZATION, WE ACHIEVE BLESSED SPEED ++

Architecture: Multi-layer performance optimization with real-time monitoring
Performance Level: Enterprise Grade with Sub-10ms Response Times
Sacred Author: Tech-Priest Performance-Mechanicus
万机之神保佑此性能模块 (May the Omnissiah bless this performance module)
"""

from .advanced_caching import (
    CacheLevel, CacheStrategy, CacheEvent, CacheEntry, CacheStats,
    CacheConfig, IntelligentCacheManager, cached, get_cache_manager,
    initialize_cache_manager
)

from .monitoring import (
    PerformanceMonitor, MetricType, PerformanceMetric, PerformanceAlert,
    MonitoringConfig, get_performance_monitor, initialize_performance_monitor
)

from .optimization import (
    PerformanceOptimizer, OptimizationStrategy, PerformanceProfile,
    PerformanceBottleneck, get_performance_optimizer, initialize_performance_optimizer
)

__all__ = [
    # Advanced Caching
    'CacheLevel', 'CacheStrategy', 'CacheEvent', 'CacheEntry', 'CacheStats',
    'CacheConfig', 'IntelligentCacheManager', 'cached', 'get_cache_manager',
    'initialize_cache_manager',
    
    # Performance Monitoring
    'PerformanceMonitor', 'MetricType', 'PerformanceMetric', 'PerformanceAlert',
    'MonitoringConfig', 'get_performance_monitor', 'initialize_performance_monitor',
    
    # Performance Optimization
    'PerformanceOptimizer', 'OptimizationStrategy', 'PerformanceProfile',
    'PerformanceBottleneck', 'get_performance_optimizer', 'initialize_performance_optimizer'
]