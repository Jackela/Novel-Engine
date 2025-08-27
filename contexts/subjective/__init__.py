#!/usr/bin/env python3
"""
Subjective Bounded Context

This bounded context handles subjective perceptions and knowledge management
in the game world. It manages how different entities perceive and understand
the game state based on their perspective, knowledge, and awareness.

Key Components:
- TurnBrief: Aggregate representing an entity's subjective view of game state
- FogOfWarService: Domain service for managing visibility and information filtering
- Perception and awareness management
- Knowledge propagation and revelation mechanics

The Subjective context is responsible for ensuring that each entity in the
game has an appropriate and consistent view of the world based on their
capabilities, position, and previously acquired knowledge.
"""