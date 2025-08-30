"""
Interaction Engine System - Modular Architecture
===============================================

Enterprise-grade modular interaction processing engine for dynamic character interactions.

Components:
- Core Types & Data Models: Interaction enums, dataclasses, and configuration
- Interaction Validator: Context validation and prerequisite checking
- Interaction Processor: Phase management and processing orchestration
- Type Processors: Category-specific interaction handlers
- State Manager: Character state updates and memory management
- Queue Manager: Interaction scheduling and priority management
- Main Facade: Unified interface maintaining backward compatibility
"""

# Core components
from .core import (
    InteractionContext,
    InteractionEngineConfig,
    InteractionOutcome,
    InteractionPhase,
    InteractionPriority,
    InteractionType,
)

# Factory functions
# Main facade
from .interaction_engine_modular import (
    InteractionEngine,
    create_interaction_engine,
    create_performance_optimized_config,
)
from .processing import InteractionProcessor
from .queue_management import QueueManager
from .state_management import StateManager
from .type_processors import InteractionTypeProcessorManager

# Component imports for advanced usage
from .validation import InteractionValidator

__all__ = [
    # Core types
    "InteractionType",
    "InteractionPriority",
    "InteractionContext",
    "InteractionPhase",
    "InteractionOutcome",
    "InteractionEngineConfig",
    # Main engine
    "InteractionEngine",
    # Factory functions
    "create_interaction_engine",
    "create_performance_optimized_config",
    # Advanced components
    "InteractionValidator",
    "InteractionProcessor",
    "InteractionTypeProcessorManager",
    "StateManager",
    "QueueManager",
]

__version__ = "4.0.0"
__author__ = "Novel Engine Development Team"
