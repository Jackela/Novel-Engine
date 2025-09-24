#!/usr/bin/env python3
"""
Coordinates Value Object

This module provides the Coordinates value object for representing spatial
positions in the World context. Following Domain-Driven Design principles,
this value object is immutable and encapsulates coordinate-related logic.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, Union


@dataclass(frozen=True)
class Coordinates:
    """
    Immutable value object representing a position in 3D space.

    This value object encapsulates spatial coordinates and provides
    coordinate-related calculations and validations.

    Attributes:
        x: X-coordinate (typically east-west axis)
        y: Y-coordinate (typically north-south axis)
        z: Z-coordinate (typically elevation/height)
        precision: Number of decimal places for coordinate precision
    """

    x: float
    y: float
    z: float = 0.0
    precision: int = field(default=6, compare=False)

    def __post_init__(self) -> None:
        """
        Validate coordinates after initialization.

        Raises:
            ValueError: If coordinates are invalid
        """
        self._validate()

        # Round coordinates to specified precision
        object.__setattr__(self, "x", round(self.x, self.precision))
        object.__setattr__(self, "y", round(self.y, self.precision))
        object.__setattr__(self, "z", round(self.z, self.precision))

    def _validate(self) -> None:
        """
        Validate coordinate values.

        Raises:
            ValueError: If coordinates are invalid
        """
        errors = []

        # Check for valid numeric values first
        coords_are_numeric = True
        for coord_name, coord_value in [
            ("x", self.x),
            ("y", self.y),
            ("z", self.z),
        ]:
            if not isinstance(coord_value, (int, float)):
                errors.append(f"{coord_name} coordinate must be numeric")
                coords_are_numeric = False
            elif math.isnan(coord_value) or math.isinf(coord_value):
                errors.append(
                    f"{coord_name} coordinate must be a finite number"
                )
                coords_are_numeric = False

        # Check precision
        if (
            not isinstance(self.precision, int)
            or self.precision < 0
            or self.precision > 15
        ):
            errors.append("Precision must be an integer between 0 and 15")

        # Only validate coordinate ranges if all coordinates are numeric
        if coords_are_numeric:
            max_coord = 1e10  # Reasonable maximum for game coordinates
            if (
                abs(self.x) > max_coord
                or abs(self.y) > max_coord
                or abs(self.z) > max_coord
            ):
                errors.append(f"Coordinates must be within ±{max_coord:g}")

        if errors:
            raise ValueError(f"Invalid coordinates: {'; '.join(errors)}")

    def distance_to(self, other: "Coordinates") -> float:
        """
        Calculate the Euclidean distance to another coordinate.

        Args:
            other: The other coordinate point

        Returns:
            Distance between the two points

        Raises:
            TypeError: If other is not a Coordinates instance
        """
        if not isinstance(other, Coordinates):
            raise TypeError(
                "Can only calculate distance to another Coordinates object"
            )

        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z

        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def distance_to_2d(self, other: "Coordinates") -> float:
        """
        Calculate the 2D distance (ignoring Z-coordinate) to another coordinate.

        Args:
            other: The other coordinate point

        Returns:
            2D distance between the two points

        Raises:
            TypeError: If other is not a Coordinates instance
        """
        if not isinstance(other, Coordinates):
            raise TypeError(
                "Can only calculate distance to another Coordinates object"
            )

        dx = self.x - other.x
        dy = self.y - other.y

        return math.sqrt(dx * dx + dy * dy)

    def manhattan_distance_to(self, other: "Coordinates") -> float:
        """
        Calculate the Manhattan (taxicab) distance to another coordinate.

        Args:
            other: The other coordinate point

        Returns:
            Manhattan distance between the two points

        Raises:
            TypeError: If other is not a Coordinates instance
        """
        if not isinstance(other, Coordinates):
            raise TypeError(
                "Can only calculate distance to another Coordinates object"
            )

        return (
            abs(self.x - other.x)
            + abs(self.y - other.y)
            + abs(self.z - other.z)
        )

    def is_within_range(
        self, other: "Coordinates", max_distance: float
    ) -> bool:
        """
        Check if another coordinate is within a specified range.

        Args:
            other: The other coordinate point
            max_distance: Maximum allowed distance

        Returns:
            True if the other coordinate is within range

        Raises:
            TypeError: If other is not a Coordinates instance
            ValueError: If max_distance is negative
        """
        if max_distance < 0:
            raise ValueError("Maximum distance cannot be negative")

        return self.distance_to(other) <= max_distance

    def translate(
        self, dx: float, dy: float, dz: float = 0.0
    ) -> "Coordinates":
        """
        Create a new Coordinates object translated by the given offsets.

        Args:
            dx: Offset in X direction
            dy: Offset in Y direction
            dz: Offset in Z direction (default: 0.0)

        Returns:
            New Coordinates object with translated position
        """
        return Coordinates(
            x=self.x + dx,
            y=self.y + dy,
            z=self.z + dz,
            precision=self.precision,
        )

    def midpoint(self, other: "Coordinates") -> "Coordinates":
        """
        Calculate the midpoint between this and another coordinate.

        Args:
            other: The other coordinate point

        Returns:
            New Coordinates object representing the midpoint

        Raises:
            TypeError: If other is not a Coordinates instance
        """
        if not isinstance(other, Coordinates):
            raise TypeError(
                "Can only calculate midpoint with another Coordinates object"
            )

        return Coordinates(
            x=(self.x + other.x) / 2,
            y=(self.y + other.y) / 2,
            z=(self.z + other.z) / 2,
            precision=min(self.precision, other.precision),
        )

    def to_tuple(self) -> Tuple[float, float, float]:
        """
        Convert coordinates to a tuple.

        Returns:
            Tuple of (x, y, z) coordinates
        """
        return (self.x, self.y, self.z)

    def to_tuple_2d(self) -> Tuple[float, float]:
        """
        Convert coordinates to a 2D tuple (ignoring Z).

        Returns:
            Tuple of (x, y) coordinates
        """
        return (self.x, self.y)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert coordinates to dictionary representation.

        Returns:
            Dictionary representation of the coordinates
        """
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "precision": self.precision,
        }

    @classmethod
    def from_tuple(
        cls,
        coords: Union[Tuple[float, float], Tuple[float, float, float]],
        precision: int = 6,
    ) -> "Coordinates":
        """
        Create Coordinates from a tuple.

        Args:
            coords: Tuple of (x, y) or (x, y, z) coordinates
            precision: Precision for coordinate values

        Returns:
            New Coordinates object

        Raises:
            ValueError: If tuple has invalid length
        """
        if len(coords) == 2:
            return cls(x=coords[0], y=coords[1], z=0.0, precision=precision)
        elif len(coords) == 3:
            return cls(
                x=coords[0], y=coords[1], z=coords[2], precision=precision
            )
        else:
            raise ValueError("Coordinate tuple must have 2 or 3 elements")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Coordinates":
        """
        Create Coordinates from dictionary representation.

        Args:
            data: Dictionary with coordinate data

        Returns:
            New Coordinates object

        Raises:
            KeyError: If required keys are missing
        """
        return cls(
            x=data["x"],
            y=data["y"],
            z=data.get("z", 0.0),
            precision=data.get("precision", 6),
        )

    @classmethod
    def origin(cls, precision: int = 6) -> "Coordinates":
        """
        Create Coordinates representing the origin (0, 0, 0).

        Args:
            precision: Precision for coordinate values

        Returns:
            Coordinates object at origin
        """
        return cls(x=0.0, y=0.0, z=0.0, precision=precision)

    def __str__(self) -> str:
        """
        String representation of the coordinates.

        Returns:
            String representation in format "(x, y, z)"
        """
        return f"({self.x}, {self.y}, {self.z})"

    def __repr__(self) -> str:
        """
        Detailed string representation of the coordinates.

        Returns:
            Detailed string representation
        """
        return (
            f"Coordinates(x={self.x}, y={self.y}, z={self.z}, "
            f"precision={self.precision})"
        )

    def __add__(self, other: "Coordinates") -> "Coordinates":
        """
        Add two coordinate values (vector addition).

        Args:
            other: Coordinates to add

        Returns:
            New Coordinates with added values

        Raises:
            TypeError: If other is not a Coordinates instance
        """
        if not isinstance(other, Coordinates):
            raise TypeError("Can only add Coordinates to Coordinates")

        return Coordinates(
            x=self.x + other.x,
            y=self.y + other.y,
            z=self.z + other.z,
            precision=min(self.precision, other.precision),
        )

    def __sub__(self, other: "Coordinates") -> "Coordinates":
        """
        Subtract two coordinate values (vector subtraction).

        Args:
            other: Coordinates to subtract

        Returns:
            New Coordinates with subtracted values

        Raises:
            TypeError: If other is not a Coordinates instance
        """
        if not isinstance(other, Coordinates):
            raise TypeError("Can only subtract Coordinates from Coordinates")

        return Coordinates(
            x=self.x - other.x,
            y=self.y - other.y,
            z=self.z - other.z,
            precision=min(self.precision, other.precision),
        )

    def __mul__(self, scalar: Union[int, float]) -> "Coordinates":
        """
        Multiply coordinates by a scalar value.

        Args:
            scalar: Scalar value to multiply by

        Returns:
            New Coordinates with scaled values

        Raises:
            TypeError: If scalar is not numeric
        """
        if not isinstance(scalar, (int, float)):
            raise TypeError("Can only multiply Coordinates by numeric values")

        return Coordinates(
            x=self.x * scalar,
            y=self.y * scalar,
            z=self.z * scalar,
            precision=self.precision,
        )

    def __rmul__(self, scalar: Union[int, float]) -> "Coordinates":
        """
        Right multiplication (scalar * coordinates).

        Args:
            scalar: Scalar value to multiply by

        Returns:
            New Coordinates with scaled values
        """
        return self.__mul__(scalar)
