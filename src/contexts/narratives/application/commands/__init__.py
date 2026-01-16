#!/usr/bin/env python3
"""
Narrative Application Commands

This package contains command objects for narrative operations in the CQRS pattern.
Commands represent intent to change state and are immutable data structures.
"""

from .narrative_arc_commands import (
    ActivateContextCommand,
    AddCharacterToArcCommand,
    AddNarrativeContextCommand,
    AddPacingSegmentCommand,
    AddPlotPointCommand,
    AddThemeCommand,
    AnalyzeCausalityCommand,
    AnalyzeNarrativeFlowCommand,
    CompleteNarrativeArcCommand,
    CreateNarrativeArcCommand,
    DeactivateContextCommand,
    DevelopThemeCommand,
    EstablishCausalLinkCommand,
    OptimizeSequenceCommand,
    RemoveCausalLinkCommand,
    RemovePlotPointCommand,
    StartNarrativeArcCommand,
    UpdateNarrativeArcCommand,
    UpdatePlotPointCommand,
)

__all__ = [
    "CreateNarrativeArcCommand",
    "UpdateNarrativeArcCommand",
    "AddPlotPointCommand",
    "UpdatePlotPointCommand",
    "RemovePlotPointCommand",
    "AddThemeCommand",
    "DevelopThemeCommand",
    "AddPacingSegmentCommand",
    "AddNarrativeContextCommand",
    "ActivateContextCommand",
    "DeactivateContextCommand",
    "AddCharacterToArcCommand",
    "StartNarrativeArcCommand",
    "CompleteNarrativeArcCommand",
    "AnalyzeNarrativeFlowCommand",
    "OptimizeSequenceCommand",
    "EstablishCausalLinkCommand",
    "RemoveCausalLinkCommand",
    "AnalyzeCausalityCommand",
]

__version__ = "1.0.0"
