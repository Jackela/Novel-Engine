#!/usr/bin/env python3
"""Location Domain Entity.

This module defines the Location entity which represents places and areas
within the world, including settlements, natural features, dungeons, and
other points of interest.

Typical usage example:
    >>> from src.contexts.world.domain.entities import Location, LocationType
    >>> city = Location.create_city(
    ...     name="Thornhaven",
    ...     population=75000,
    ...     climate=ClimateType.TEMPERATE
    ... )
    >>> dungeon = Location.create_dungeon(
    ...     name="Crypt of Shadows",
    ...     dangers=["undead", "traps", "cursed artifacts"]
    ... )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .entity import Entity


class LocationType(Enum):
    """Classification of location types.

    Determines the nature and expected characteristics of a location,
    affecting population limits, danger levels, and resource availability.

    Attributes:
        CONTINENT: Massive landmass containing multiple regions.
        REGION: Large geographic area with shared characteristics.
        COUNTRY: Political entity with defined borders.
        PROVINCE: Administrative division of a country.
        CITY: Large urban settlement (population up to 5 million).
        TOWN: Medium settlement (population up to 50,000).
        VILLAGE: Small settlement (population up to 5,000).
        FORTRESS: Military stronghold or castle.
        CASTLE: Noble residence, often fortified.
        DUNGEON: Underground complex, often dangerous.
        TEMPLE: Religious structure or complex.
        FOREST: Wooded natural area.
        MOUNTAIN: Elevated terrain feature.
        OCEAN: Large body of saltwater.
        RIVER: Flowing freshwater body.
        DESERT: Arid wasteland.
        SWAMP: Wetland with standing water.
        PLAINS: Flat grassland terrain.
        ISLAND: Land surrounded by water.
        CAVE: Natural underground formation.
        RUINS: Remnants of former structures.
        LANDMARK: Notable geographic or artificial feature.
        CAPITAL: Seat of government, largest city.
        PORT: Coastal trading settlement.
        SPACE_STATION: Orbital or space-based structure.
        PLANET: Celestial body (for sci-fi settings).
        DIMENSION: Alternate plane of existence.
    """

    CONTINENT = "continent"
    REGION = "region"
    COUNTRY = "country"
    PROVINCE = "province"
    CITY = "city"
    TOWN = "town"
    VILLAGE = "village"
    FORTRESS = "fortress"
    CASTLE = "castle"
    DUNGEON = "dungeon"
    TEMPLE = "temple"
    FOREST = "forest"
    MOUNTAIN = "mountain"
    OCEAN = "ocean"
    RIVER = "river"
    DESERT = "desert"
    SWAMP = "swamp"
    PLAINS = "plains"
    ISLAND = "island"
    CAVE = "cave"
    RUINS = "ruins"
    LANDMARK = "landmark"
    CAPITAL = "capital"
    PORT = "port"
    SPACE_STATION = "space_station"
    PLANET = "planet"
    DIMENSION = "dimension"


class ClimateType(Enum):
    """Climate classification for locations.

    Affects environmental descriptions, available resources, and
    inhabitant lifestyles.

    Attributes:
        TROPICAL: Hot and humid, rainforests.
        TEMPERATE: Moderate temperatures, four seasons.
        ARCTIC: Extremely cold, ice and snow.
        DESERT: Hot and dry, minimal precipitation.
        MEDITERRANEAN: Warm, dry summers; mild, wet winters.
        CONTINENTAL: Hot summers, cold winters, inland areas.
        OCEANIC: Mild temperatures, frequent rain, coastal.
        SUBARCTIC: Very cold winters, short cool summers.
        MAGICAL: Climate maintained or created by magic.
        ARTIFICIAL: Climate-controlled environments.
    """

    TROPICAL = "tropical"
    TEMPERATE = "temperate"
    ARCTIC = "arctic"
    DESERT = "desert"
    MEDITERRANEAN = "mediterranean"
    CONTINENTAL = "continental"
    OCEANIC = "oceanic"
    SUBARCTIC = "subarctic"
    MAGICAL = "magical"
    ARTIFICIAL = "artificial"


class LocationStatus(Enum):
    """Current status of the location.

    Represents the current state of habitability and prosperity
    of a location.

    Attributes:
        THRIVING: Prosperous and growing.
        STABLE: Maintaining steady conditions.
        DECLINING: Losing population or resources.
        ABANDONED: No longer inhabited.
        DESTROYED: Ruined beyond habitation.
        CONTESTED: Subject to ongoing conflict.
        HIDDEN: Concealed from general knowledge.
        SEALED: Magically or physically blocked.
        UNDER_CONSTRUCTION: Being built or rebuilt.
    """

    THRIVING = "thriving"
    STABLE = "stable"
    DECLINING = "declining"
    ABANDONED = "abandoned"
    DESTROYED = "destroyed"
    CONTESTED = "contested"
    HIDDEN = "hidden"
    SEALED = "sealed"
    UNDER_CONSTRUCTION = "under_construction"


@dataclass(eq=False)
class Location(Entity):
    """Location Entity.

    Represents a place within the world with its physical characteristics,
    inhabitants, and narrative significance. Contains domain logic for
    managing location hierarchies and relationships.

    Attributes:
        name: The location's name
        description: Detailed description of the location
        location_type: Classification of location
        climate: Climate type (if applicable)
        status: Current status of the location
        parent_location_id: ID of containing location (for hierarchy)
        child_location_ids: IDs of locations contained within this one
        controlling_faction_id: ID of faction that controls this location
        population: Population count (if applicable)
        notable_features: List of notable features/landmarks
        resources: Resources available at this location
        dangers: Known dangers or hazards
        history_notes: Brief historical notes
        coordinates: Optional coordinate string (e.g., "x,y" or "lat,long")
        accessibility: How accessible the location is (0-100)
        wealth_level: Economic prosperity (0-100)
        magic_concentration: Level of magical energy (0-100)
        connections: IDs of connected locations (roads, portals, etc.)
    """

    name: str = ""
    description: str = ""
    location_type: LocationType = LocationType.REGION
    climate: Optional[ClimateType] = None
    status: LocationStatus = LocationStatus.STABLE
    parent_location_id: Optional[str] = None
    child_location_ids: List[str] = field(default_factory=list)
    controlling_faction_id: Optional[str] = None
    population: int = 0
    notable_features: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    dangers: List[str] = field(default_factory=list)
    history_notes: List[str] = field(default_factory=list)
    coordinates: Optional[str] = None
    accessibility: int = 50
    wealth_level: int = 50
    magic_concentration: int = 0
    connections: List[str] = field(default_factory=list)

    def __eq__(self, other: object) -> bool:
        """Equality comparison based on entity identity (inherited from Entity)."""
        return super().__eq__(other)

    def _validate_business_rules(self) -> List[str]:
        """Validate Location-specific business rules."""
        errors = []

        if not self.name or not self.name.strip():
            errors.append("Location name cannot be empty")

        if len(self.name) > 200:
            errors.append("Location name cannot exceed 200 characters")

        if self.population < 0:
            errors.append("Population cannot be negative")

        if not 0 <= self.accessibility <= 100:
            errors.append("Accessibility must be between 0 and 100")

        if not 0 <= self.wealth_level <= 100:
            errors.append("Wealth level must be between 0 and 100")

        if not 0 <= self.magic_concentration <= 100:
            errors.append("Magic concentration must be between 0 and 100")

        # Validate type-specific rules
        errors.extend(self._validate_type_specific_rules())

        # Validate hierarchy consistency
        errors.extend(self._validate_hierarchy())

        return errors

    def _validate_type_specific_rules(self) -> List[str]:
        """Validate rules specific to location type."""
        errors = []

        # Settlements should have population
        settlement_types = {
            LocationType.CITY,
            LocationType.TOWN,
            LocationType.VILLAGE,
            LocationType.CAPITAL,
        }
        if self.location_type in settlement_types and self.population == 0:
            # Warning but allowed - could be newly founded or abandoned
            pass

        # Natural locations typically don't have wealth level
        natural_types = {
            LocationType.FOREST,
            LocationType.MOUNTAIN,
            LocationType.OCEAN,
            LocationType.RIVER,
            LocationType.DESERT,
            LocationType.SWAMP,
            LocationType.PLAINS,
        }
        if self.location_type in natural_types and self.wealth_level > 50:
            # This is allowed - could have valuable resources
            pass

        # Population limits by type
        max_populations = {
            LocationType.VILLAGE: 5000,
            LocationType.TOWN: 50000,
            LocationType.CITY: 5000000,
            LocationType.CAPITAL: 10000000,
        }
        if self.location_type in max_populations:
            if self.population > max_populations[self.location_type]:
                errors.append(
                    f"{self.location_type.value} population seems too high "
                    f"(max typical: {max_populations[self.location_type]})"
                )

        return errors

    def _validate_hierarchy(self) -> List[str]:
        """Validate location hierarchy consistency."""
        errors = []

        # Can't be own parent
        if self.parent_location_id == self.id:
            errors.append("Location cannot be its own parent")

        # Can't contain itself
        if self.id in self.child_location_ids:
            errors.append("Location cannot contain itself")

        return errors

    def add_child_location(self, location_id: str) -> None:
        """
        Add a child location.

        Args:
            location_id: ID of the child location

        Raises:
            ValueError: If adding self as child
        """
        if location_id == self.id:
            raise ValueError("Location cannot contain itself")

        if location_id not in self.child_location_ids:
            self.child_location_ids.append(location_id)
            self.touch()

    def remove_child_location(self, location_id: str) -> bool:
        """
        Remove a child location.

        Args:
            location_id: ID of the child to remove

        Returns:
            True if removed, False if not found
        """
        if location_id in self.child_location_ids:
            self.child_location_ids.remove(location_id)
            self.touch()
            return True
        return False

    def set_parent_location(self, parent_id: Optional[str]) -> None:
        """
        Set the parent location.

        Args:
            parent_id: ID of the parent location, or None to remove
        """
        if parent_id == self.id:
            raise ValueError("Location cannot be its own parent")

        self.parent_location_id = parent_id
        self.touch()

    def add_connection(self, location_id: str) -> None:
        """
        Add a connection to another location.

        Args:
            location_id: ID of the location to connect to
        """
        if location_id != self.id and location_id not in self.connections:
            self.connections.append(location_id)
            self.touch()

    def remove_connection(self, location_id: str) -> bool:
        """
        Remove a connection to another location.

        Args:
            location_id: ID of the location to disconnect

        Returns:
            True if removed, False if not found
        """
        if location_id in self.connections:
            self.connections.remove(location_id)
            self.touch()
            return True
        return False

    def add_notable_feature(self, feature: str) -> None:
        """
        Add a notable feature to the location.

        Args:
            feature: The feature to add
        """
        if not feature or not feature.strip():
            raise ValueError("Feature cannot be empty")

        feature = feature.strip()
        if feature not in self.notable_features:
            self.notable_features.append(feature)
            self.touch()

    def add_danger(self, danger: str) -> None:
        """
        Add a danger/hazard to the location.

        Args:
            danger: The danger to add
        """
        if not danger or not danger.strip():
            raise ValueError("Danger cannot be empty")

        danger = danger.strip()
        if danger not in self.dangers:
            self.dangers.append(danger)
            self.touch()

    def update_population(self, new_population: int) -> None:
        """
        Update the location's population.

        Args:
            new_population: New population count

        Raises:
            ValueError: If population is negative
        """
        if new_population < 0:
            raise ValueError("Population cannot be negative")

        self.population = new_population
        self.touch()

    def set_controlling_faction(self, faction_id: Optional[str]) -> None:
        """
        Set the controlling faction for this location.

        Args:
            faction_id: ID of the controlling faction, or None
        """
        self.controlling_faction_id = faction_id
        self.touch()

    def update_status(self, new_status: LocationStatus) -> None:
        """
        Update the location's status.

        Args:
            new_status: New status
        """
        if new_status != self.status:
            self.status = new_status
            self.touch()

    def is_settlement(self) -> bool:
        """Check if location is a settlement (has permanent inhabitants)."""
        return self.location_type in {
            LocationType.CITY,
            LocationType.TOWN,
            LocationType.VILLAGE,
            LocationType.CAPITAL,
            LocationType.PORT,
            LocationType.FORTRESS,
        }

    def is_natural(self) -> bool:
        """Check if location is a natural feature."""
        return self.location_type in {
            LocationType.FOREST,
            LocationType.MOUNTAIN,
            LocationType.OCEAN,
            LocationType.RIVER,
            LocationType.DESERT,
            LocationType.SWAMP,
            LocationType.PLAINS,
            LocationType.ISLAND,
            LocationType.CAVE,
        }

    def is_point_of_interest(self) -> bool:
        """Check if location is a point of interest (dungeon, ruins, etc.)."""
        return self.location_type in {
            LocationType.DUNGEON,
            LocationType.TEMPLE,
            LocationType.RUINS,
            LocationType.LANDMARK,
            LocationType.CAVE,
        }

    def is_accessible(self) -> bool:
        """Check if location is reasonably accessible (accessibility >= 50)."""
        return self.accessibility >= 50

    def is_dangerous(self) -> bool:
        """Check if location has known dangers."""
        return len(self.dangers) > 0

    def get_danger_level(self) -> str:
        """
        Get a qualitative danger level.

        Returns:
            Danger level description
        """
        danger_count = len(self.dangers)
        if danger_count == 0:
            return "safe"
        elif danger_count <= 2:
            return "cautionary"
        elif danger_count <= 5:
            return "dangerous"
        else:
            return "deadly"

    def _to_dict_specific(self) -> Dict[str, Any]:
        """Convert Location-specific data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "location_type": self.location_type.value,
            "climate": self.climate.value if self.climate else None,
            "status": self.status.value,
            "parent_location_id": self.parent_location_id,
            "child_location_ids": self.child_location_ids,
            "controlling_faction_id": self.controlling_faction_id,
            "population": self.population,
            "notable_features": self.notable_features,
            "resources": self.resources,
            "dangers": self.dangers,
            "history_notes": self.history_notes,
            "coordinates": self.coordinates,
            "accessibility": self.accessibility,
            "wealth_level": self.wealth_level,
            "magic_concentration": self.magic_concentration,
            "connections": self.connections,
        }

    @classmethod
    def create_city(
        cls,
        name: str,
        description: str = "",
        population: int = 50000,
        climate: ClimateType = ClimateType.TEMPERATE,
    ) -> "Location":
        """Create a city location with typical urban attributes.

        Factory method that creates a pre-configured Location representing
        a thriving urban center with high accessibility and moderate wealth.

        Args:
            name: The city's name.
            description: Optional detailed description.
            population: Number of inhabitants. Defaults to 50,000.
            climate: Climate type. Defaults to TEMPERATE.

        Returns:
            A new Location configured as a city.

        Example:
            >>> city = Location.create_city(
            ...     name="Thornhaven",
            ...     population=100000,
            ...     climate=ClimateType.MEDITERRANEAN
            ... )
        """
        return cls(
            name=name,
            description=description,
            location_type=LocationType.CITY,
            climate=climate,
            status=LocationStatus.THRIVING,
            population=population,
            accessibility=80,
            wealth_level=60,
        )

    @classmethod
    def create_dungeon(
        cls,
        name: str,
        description: str = "",
        dangers: List[str] | None = None,
    ) -> "Location":
        """Create a dungeon location with typical underground attributes.

        Factory method that creates a pre-configured Location representing
        a dangerous underground complex with low accessibility, moderate
        treasure potential, and magical presence.

        Args:
            name: The dungeon's name.
            description: Optional detailed description.
            dangers: List of hazards. Defaults to ["traps", "monsters"].

        Returns:
            A new Location configured as a dungeon.

        Example:
            >>> dungeon = Location.create_dungeon(
            ...     name="Crypt of Shadows",
            ...     dangers=["undead", "poison gas", "collapsing floors"]
            ... )
        """
        return cls(
            name=name,
            description=description,
            location_type=LocationType.DUNGEON,
            status=LocationStatus.STABLE,
            population=0,
            accessibility=20,
            wealth_level=30,
            magic_concentration=40,
            dangers=dangers or ["traps", "monsters"],
        )

    @classmethod
    def create_natural_area(
        cls,
        name: str,
        location_type: LocationType,
        description: str = "",
        climate: ClimateType = ClimateType.TEMPERATE,
    ) -> "Location":
        """Create a natural area with typical wilderness attributes.

        Factory method that creates a pre-configured Location representing
        a natural terrain feature with no population and moderate accessibility.

        Args:
            name: The area's name.
            location_type: The type of natural feature (FOREST, MOUNTAIN, etc.).
            description: Optional detailed description.
            climate: Climate type. Defaults to TEMPERATE.

        Returns:
            A new Location configured as a natural area.

        Example:
            >>> forest = Location.create_natural_area(
            ...     name="Whispering Woods",
            ...     location_type=LocationType.FOREST,
            ...     climate=ClimateType.TEMPERATE
            ... )
        """
        return cls(
            name=name,
            description=description,
            location_type=location_type,
            climate=climate,
            status=LocationStatus.STABLE,
            population=0,
            accessibility=40,
            wealth_level=20,
        )
