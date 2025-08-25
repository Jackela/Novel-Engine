"""
Novel Engine - Advanced AI Narrative Generation Platform
========================================================

Core package for Novel Engine providing:
- Multi-agent narrative generation
- Subjective reality modeling
- Real-time story coordination
- Production-ready infrastructure

Version: 2.0.0
"""

__version__ = "2.0.0"
__author__ = "Novel Engine Team"
__description__ = "Advanced AI Narrative Generation Platform"

# Core exports
from .core.subjective_reality import SubjectiveRealityEngine
from .core.emergent_narrative import EmergentNarrativeSystem
from .infrastructure.state_store import UnifiedStateManager
from .infrastructure.observability import MetricsCollector

__all__ = [
    "SubjectiveRealityEngine",
    "EmergentNarrativeSystem", 
    "UnifiedStateManager",
    "MetricsCollector"
]