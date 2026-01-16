#!/usr/bin/env python3
"""
Narrative Domain Events Package

This package contains domain events that represent significant occurrences
within the Narrative bounded context.

Key Domain Events:
- NarrativeArcCreated: New narrative arc established
- PlotPointAdded: Plot point added to narrative arc
- ThemeIntroduced: New theme introduced to narrative
- CausalLinkEstablished: Cause-and-effect relationship created
- NarrativeFlowChanged: Story flow or pacing modified
- ContextUpdated: Narrative context information changed
"""

from .narrative_events import (
    CausalLinkEstablished,
    CausalLinkRemoved,
    ContextActivated,
    ContextDeactivated,
    ContextUpdated,
    NarrativeArcCompleted,
    NarrativeArcCreated,
    NarrativeArcUpdated,
    NarrativeEvent,
    NarrativeFlowChanged,
    PacingAdjusted,
    PlotPointAdded,
    PlotPointRemoved,
    PlotPointUpdated,
    ThemeIntensityChanged,
    ThemeIntroduced,
    ThemeResolved,
)

__all__ = [
    # Base event
    "NarrativeEvent",
    # Narrative Arc events
    "NarrativeArcCreated",
    "NarrativeArcUpdated",
    "NarrativeArcCompleted",
    # Plot Point events
    "PlotPointAdded",
    "PlotPointUpdated",
    "PlotPointRemoved",
    # Theme events
    "ThemeIntroduced",
    "ThemeIntensityChanged",
    "ThemeResolved",
    # Causal events
    "CausalLinkEstablished",
    "CausalLinkRemoved",
    # Flow and Pacing events
    "NarrativeFlowChanged",
    "PacingAdjusted",
    # Context events
    "ContextUpdated",
    "ContextActivated",
    "ContextDeactivated",
]

__version__ = "1.0.0"
