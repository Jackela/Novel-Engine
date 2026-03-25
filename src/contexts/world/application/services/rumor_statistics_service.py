"""Rumor statistics calculation.

This module provides statistics tracking and calculation for rumor propagation.
"""

from dataclasses import dataclass
from typing import List, Optional

from src.contexts.world.domain.entities.rumor import Rumor
from src.core.result import Err, Error, Ok, Result


@dataclass
class RumorStatistics:
    """Statistics about rumors in a world.

    Attributes:
        total_rumors: Total number of rumors (including dead)
        active_rumors: Number of active rumors (truth_value > 0)
        avg_truth: Average truth value of active rumors
        most_spread: Rumor with highest spread_count (or None if no rumors)
        dead_rumors: Number of dead rumors (truth_value == 0)
    """

    total_rumors: int = 0
    active_rumors: int = 0
    avg_truth: float = 0.0
    most_spread: Optional[Rumor] = None
    dead_rumors: int = 0


class RumorStatisticsService:
    """Calculates and tracks statistics about rumors.

    This service provides methods to analyze collections of rumors
    and calculate aggregate statistics.
    """

    def calculate_statistics(self, rumors: List[Rumor]) -> Result[RumorStatistics]:
        """Calculate statistics about a list of rumors.

        Args:
            rumors: List of Rumor entities to analyze

        Returns:
            Result containing:
            - Ok: RumorStatistics with calculated values
            - Err: Error if calculation fails
        """
        try:
            if not rumors:
                return Ok(RumorStatistics())

            active_rumors = [r for r in rumors if not r.is_dead]
            dead_rumors = [r for r in rumors if r.is_dead]

            avg_truth = 0.0
            if active_rumors:
                avg_truth = sum(r.truth_value for r in active_rumors) / len(
                    active_rumors
                )

            most_spread: Optional[Rumor] = None
            if rumors:
                most_spread = max(rumors, key=lambda r: r.spread_count)

            return Ok(
                RumorStatistics(
                    total_rumors=len(rumors),
                    active_rumors=len(active_rumors),
                    avg_truth=round(avg_truth, 2),
                    most_spread=most_spread,
                    dead_rumors=len(dead_rumors),
                )
            )
        except Exception as e:
            return Err(
                Error(
                    message=f"Failed to calculate rumor statistics: {e}",
                    code="STATISTICS_CALCULATION_ERROR",
                    recoverable=True,
                )
            )

    def get_most_spread(self, rumors: List[Rumor]) -> Optional[Rumor]:
        """Get the most spread rumor from a list.

        Args:
            rumors: List of rumors to analyze

        Returns:
            Rumor with highest spread_count, or None if list is empty
        """
        if not rumors:
            return None
        return max(rumors, key=lambda r: r.spread_count)

    def get_average_truth(self, rumors: List[Rumor]) -> float:
        """Get average truth value of active rumors.

        Args:
            rumors: List of rumors to analyze

        Returns:
            Average truth value (0.0 if no active rumors)
        """
        active_rumors = [r for r in rumors if not r.is_dead]
        if not active_rumors:
            return 0.0
        return sum(r.truth_value for r in active_rumors) / len(active_rumors)

    def count_active(self, rumors: List[Rumor]) -> int:
        """Count active rumors in a list.

        Args:
            rumors: List of rumors to count

        Returns:
            Number of rumors with truth_value > 0
        """
        return len([r for r in rumors if not r.is_dead])

    def count_dead(self, rumors: List[Rumor]) -> int:
        """Count dead rumors in a list.

        Args:
            rumors: List of rumors to count

        Returns:
            Number of rumors with truth_value == 0
        """
        return len([r for r in rumors if r.is_dead])

    def get_truth_distribution(self, rumors: List[Rumor]) -> dict[str, int]:
        """Get distribution of truth values.

        Args:
            rumors: List of rumors to analyze

        Returns:
            Dictionary with count of rumors in each truth range
        """
        distribution = {
            "dead (0)": 0,
            "low (1-30)": 0,
            "medium (31-60)": 0,
            "high (61-90)": 0,
            "perfect (91-100)": 0,
        }

        for rumor in rumors:
            truth = rumor.truth_value
            if truth == 0:
                distribution["dead (0)"] += 1
            elif truth <= 30:
                distribution["low (1-30)"] += 1
            elif truth <= 60:
                distribution["medium (31-60)"] += 1
            elif truth <= 90:
                distribution["high (61-90)"] += 1
            else:
                distribution["perfect (91-100)"] += 1

        return distribution

    def get_spread_distribution(self, rumors: List[Rumor]) -> dict[str, int]:
        """Get distribution of spread counts.

        Args:
            rumors: List of rumors to analyze

        Returns:
            Dictionary with count of rumors in each spread range
        """
        distribution = {
            "none (0)": 0,
            "low (1-5)": 0,
            "medium (6-15)": 0,
            "high (16-30)": 0,
            "viral (31+)": 0,
        }

        for rumor in rumors:
            spread = rumor.spread_count
            if spread == 0:
                distribution["none (0)"] += 1
            elif spread <= 5:
                distribution["low (1-5)"] += 1
            elif spread <= 15:
                distribution["medium (6-15)"] += 1
            elif spread <= 30:
                distribution["high (16-30)"] += 1
            else:
                distribution["viral (31+)"] += 1

        return distribution
