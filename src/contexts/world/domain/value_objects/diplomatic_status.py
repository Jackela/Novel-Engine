#!/usr/bin/env python3
"""
DiplomaticStatus Value Object

This module provides the DiplomaticStatus enum for representing diplomatic
relationship statuses between factions. The status is determined by a
relation strength value ranging from -100 to 100.
"""

from enum import Enum


class DiplomaticStatus(Enum):
    """Diplomatic relationship status between factions.

    This enum categorizes diplomatic relations based on a strength value
    ranging from -100 (hostile) to 100 (allied). The status affects
    faction interactions, trade, and conflict resolution.

    Strength ranges:
        - ALLIED: strength >= 50
        - FRIENDLY: 20 <= strength < 50
        - NEUTRAL: -20 < strength < 20
        - COLD: -50 < strength <= -20
        - HOSTILE: -80 < strength <= -50
        - AT_WAR: strength <= -80

    Attributes:
        ALLIED: Formal alliance with mutual defense obligations.
        FRIENDLY: Positive relations with trade and cooperation.
        NEUTRAL: No strong positive or negative relations.
        COLD: Unfriendly relations with limited interaction.
        HOSTILE: Openly antagonistic, conflict likely.
        AT_WAR: Active military conflict.
    """

    ALLIED = "allied"
    FRIENDLY = "friendly"
    NEUTRAL = "neutral"
    COLD = "cold"
    HOSTILE = "hostile"
    AT_WAR = "at_war"

    @classmethod
    def from_relation_strength(cls, strength: int) -> "DiplomaticStatus":
        """Determine diplomatic status from relation strength.

        Maps a numeric strength value to the appropriate diplomatic status
        based on predefined thresholds. The strength represents the overall
        relationship quality between two factions.

        Args:
            strength: Relation strength (-100 to 100). Values outside
                this range are clamped to the nearest boundary.

        Returns:
            The DiplomaticStatus corresponding to the strength value.

        Example:
            >>> DiplomaticStatus.from_relation_strength(75)
            <DiplomaticStatus.ALLIED: 'allied'>
            >>> DiplomaticStatus.from_relation_strength(-85)
            <DiplomaticStatus.AT_WAR: 'at_war'>
            >>> DiplomaticStatus.from_relation_strength(0)
            <DiplomaticStatus.NEUTRAL: 'neutral'>
        """
        # Clamp strength to valid range
        strength = max(-100, min(100, strength))

        if strength >= 50:
            return cls.ALLIED
        elif strength >= 20:
            return cls.FRIENDLY
        elif strength > -20:
            return cls.NEUTRAL
        elif strength > -50:
            return cls.COLD
        elif strength > -80:
            return cls.HOSTILE
        else:
            return cls.AT_WAR

    @property
    def color(self) -> str:
        """Get the UI color for this diplomatic status.

        Returns a hex color string suitable for rendering the status
        in user interfaces. Colors progress from green (positive)
        through yellow/orange to red (negative).

        Returns:
            Hex color string (e.g., '#22c55e' for ALLIED).

        Example:
            >>> DiplomaticStatus.ALLIED.color
            '#22c55e'
            >>> DiplomaticStatus.AT_WAR.color
            '#dc2626'
        """
        color_map = {
            DiplomaticStatus.ALLIED: "#22c55e",  # green-500
            DiplomaticStatus.FRIENDLY: "#84cc16",  # lime-500
            DiplomaticStatus.NEUTRAL: "#eab308",  # yellow-500
            DiplomaticStatus.COLD: "#f97316",  # orange-500
            DiplomaticStatus.HOSTILE: "#ef4444",  # red-500
            DiplomaticStatus.AT_WAR: "#dc2626",  # red-600
        }
        return color_map[self]

    @property
    def label(self) -> str:
        """Get the human-readable label for this diplomatic status.

        Returns a display-friendly string suitable for UI labels
        and accessibility descriptions.

        Returns:
            Human-readable status label (e.g., 'At War' for AT_WAR).

        Example:
            >>> DiplomaticStatus.AT_WAR.label
            'At War'
            >>> DiplomaticStatus.ALLIED.label
            'Allied'
        """
        label_map = {
            DiplomaticStatus.ALLIED: "Allied",
            DiplomaticStatus.FRIENDLY: "Friendly",
            DiplomaticStatus.NEUTRAL: "Neutral",
            DiplomaticStatus.COLD: "Cold",
            DiplomaticStatus.HOSTILE: "Hostile",
            DiplomaticStatus.AT_WAR: "At War",
        }
        return label_map[self]
