"""Coordinates value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Coordinates:
    """Geographic coordinates."""
    
    x: float
    y: float
    z: float = 0.0
    
    def distance_to(self, other: "Coordinates") -> float:
        """Calculate Euclidean distance to another point."""
        return (
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        ) ** 0.5
