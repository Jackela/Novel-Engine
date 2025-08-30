"""
Memory Platform Component
========================

Platform service for memory management, persistence, and retrieval
capabilities shared across character, narrative, and campaign systems.

Platform Responsibilities:
- Centralized memory storage and retrieval
- Memory search and similarity matching
- Cross-service memory coordination
- Memory optimization and cleanup
- Memory analytics and insights

Architecture: Platform service providing memory capabilities to all applications
Usage: Consumed by character-service, story-engine, campaign-manager
"""

__version__ = "1.0.0"
__platform_service__ = "memory"
__description__ = "Memory Management Platform Service"
