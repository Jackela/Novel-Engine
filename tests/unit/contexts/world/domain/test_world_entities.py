#!/usr/bin/env python3
"""
Unit tests for World Domain Entities

Comprehensive test suite for WorldSetting, Faction, Location, and HistoryEvent
entities, covering validation, domain logic, and business rules.
"""

import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

# Mock problematic dependencies
sys.modules["aioredis"] = MagicMock()


# Create proper mock classes for event_bus module
class MockEventPriority(Enum):
    """Mock EventPriority for testing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MockEvent:
    """Mock Event class that supports dataclass functionality."""

    event_id: str = None
    correlation_id: Optional[str] = None
    source: Optional[str] = None
    priority: MockEventPriority = MockEventPriority.NORMAL
    timestamp: datetime = None
    tags: set = field(default_factory=set)
    payload: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.event_id is None:
            self.event_id = str(uuid4())
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MockEventBusModule:
    Event = MockEvent
    EventPriority = MockEventPriority


sys.modules["src.events.event_bus"] = MockEventBusModule()

# Now import the actual modules we're testing
from src.contexts.world.domain.entities.world_setting import (  # noqa: E402
    Era,
    Genre,
    ToneType,
    WorldSetting,
)
from src.contexts.world.domain.entities.faction import (  # noqa: E402
    Faction,
    FactionAlignment,
    FactionRelation,
    FactionType,
)
from src.contexts.world.domain.entities.location import (  # noqa: E402
    ClimateType,
    Location,
    LocationStatus,
    LocationType,
)
from src.contexts.world.domain.entities.history_event import (  # noqa: E402
    EventOutcome,
    EventSignificance,
    EventType,
    HistoryEvent,
)


class TestWorldSetting:
    """Test suite for WorldSetting entity."""

    @pytest.fixture
    def world_setting(self) -> WorldSetting:
        """Create a test WorldSetting instance."""
        return WorldSetting(
            name="Test World",
            description="A test world for unit testing",
            genre=Genre.FANTASY,
            era=Era.MEDIEVAL,
            themes=["adventure", "magic"],
            tone=ToneType.HEROIC,
            magic_level=7,
            technology_level=3,
        )

    @pytest.mark.unit
    def test_create_world_setting(self, world_setting: WorldSetting):
        """Test basic WorldSetting creation."""
        assert world_setting.name == "Test World"
        assert world_setting.genre == Genre.FANTASY
        assert world_setting.era == Era.MEDIEVAL
        assert world_setting.magic_level == 7
        assert world_setting.technology_level == 3

    @pytest.mark.unit
    def test_world_setting_validation_empty_name(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            WorldSetting(name="", genre=Genre.FANTASY)

    @pytest.mark.unit
    def test_world_setting_validation_magic_level_range(self):
        """Test magic level validation."""
        with pytest.raises(ValueError, match="Magic level must be between"):
            WorldSetting(name="Test", magic_level=15)

        with pytest.raises(ValueError, match="Magic level must be between"):
            WorldSetting(name="Test", magic_level=-1)

    @pytest.mark.unit
    def test_world_setting_validation_technology_level_range(self):
        """Test technology level validation."""
        with pytest.raises(ValueError, match="Technology level must be between"):
            WorldSetting(name="Test", technology_level=15)

    @pytest.mark.unit
    def test_world_setting_genre_era_compatibility(self):
        """Test genre and era compatibility validation."""
        # Science fiction with medieval era should raise error
        with pytest.raises(ValueError, match="typically requires"):
            WorldSetting(
                name="Test",
                genre=Genre.SCIENCE_FICTION,
                era=Era.MEDIEVAL,
            )

    @pytest.mark.unit
    def test_add_theme(self, world_setting: WorldSetting):
        """Test adding themes."""
        original_version = world_setting.version
        world_setting.add_theme("heroism")

        assert "heroism" in world_setting.themes
        assert world_setting.version > original_version

    @pytest.mark.unit
    def test_add_theme_limit(self, world_setting: WorldSetting):
        """Test theme limit enforcement."""
        for i in range(10):
            try:
                world_setting.add_theme(f"theme_{i}")
            except ValueError:
                # Theme limit reached - expected for later iterations
                pass

        with pytest.raises(ValueError, match="Cannot have more than 10 themes"):
            world_setting.add_theme("one_more_theme")

    @pytest.mark.unit
    def test_add_secondary_genre(self, world_setting: WorldSetting):
        """Test adding secondary genres."""
        world_setting.add_secondary_genre(Genre.MYSTERY)
        assert Genre.MYSTERY in world_setting.secondary_genres

    @pytest.mark.unit
    def test_add_same_secondary_genre_as_primary(self, world_setting: WorldSetting):
        """Test that adding primary genre as secondary raises error."""
        with pytest.raises(ValueError, match="cannot be same as primary"):
            world_setting.add_secondary_genre(Genre.FANTASY)

    @pytest.mark.unit
    def test_is_high_magic(self, world_setting: WorldSetting):
        """Test high magic detection."""
        assert world_setting.is_high_magic() is True

        low_magic = WorldSetting(name="Low Magic", magic_level=3)
        assert low_magic.is_high_magic() is False

    @pytest.mark.unit
    def test_factory_create_fantasy_world(self):
        """Test factory method for creating fantasy world."""
        world = WorldSetting.create_fantasy_world(
            name="Fantasy Realm",
            description="A magical land",
        )
        assert world.genre == Genre.FANTASY
        assert world.era == Era.MEDIEVAL
        assert world.magic_level == 7

    @pytest.mark.unit
    def test_factory_create_scifi_world(self):
        """Test factory method for creating sci-fi world."""
        world = WorldSetting.create_scifi_world(
            name="Space Station Alpha",
            technology_level=9,
        )
        assert world.genre == Genre.SCIENCE_FICTION
        assert world.era == Era.FAR_FUTURE
        assert world.technology_level == 9
        assert world.magic_level == 0

    @pytest.mark.unit
    def test_to_dict(self, world_setting: WorldSetting):
        """Test dictionary serialization."""
        data = world_setting.to_dict()
        assert data["name"] == "Test World"
        assert data["genre"] == "fantasy"
        assert data["era"] == "medieval"


class TestFaction:
    """Test suite for Faction entity."""

    @pytest.fixture
    def faction(self) -> Faction:
        """Create a test Faction instance."""
        return Faction(
            name="Test Guild",
            description="A test guild for unit testing",
            faction_type=FactionType.GUILD,
            alignment=FactionAlignment.LAWFUL_NEUTRAL,
            influence=50,
            military_strength=30,
            economic_power=70,
        )

    @pytest.mark.unit
    def test_create_faction(self, faction: Faction):
        """Test basic Faction creation."""
        assert faction.name == "Test Guild"
        assert faction.faction_type == FactionType.GUILD
        assert faction.alignment == FactionAlignment.LAWFUL_NEUTRAL

    @pytest.mark.unit
    def test_faction_validation_empty_name(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Faction(name="")

    @pytest.mark.unit
    def test_faction_validation_influence_range(self):
        """Test influence validation."""
        with pytest.raises(ValueError, match="Influence must be between"):
            Faction(name="Test", influence=150)

    @pytest.mark.unit
    def test_add_relation(self, faction: Faction):
        """Test adding faction relations."""
        relation = FactionRelation(
            target_faction_id="other-faction-id",
            relation_type="alliance",
            strength=75,
        )
        faction.add_relation(relation)

        assert len(faction.relations) == 1
        assert faction.relations[0].target_faction_id == "other-faction-id"

    @pytest.mark.unit
    def test_update_relation(self, faction: Faction):
        """Test updating existing relation."""
        relation1 = FactionRelation(
            target_faction_id="other-id",
            relation_type="neutral",
            strength=0,
        )
        faction.add_relation(relation1)

        relation2 = FactionRelation(
            target_faction_id="other-id",
            relation_type="alliance",
            strength=80,
        )
        faction.add_relation(relation2)

        assert len(faction.relations) == 1
        assert faction.get_relation("other-id").strength == 80

    @pytest.mark.unit
    def test_get_allies_and_enemies(self, faction: Faction):
        """Test getting allies and enemies."""
        faction.add_relation(FactionRelation("ally1", "alliance", 75))
        faction.add_relation(FactionRelation("ally2", "alliance", 50))
        faction.add_relation(FactionRelation("enemy1", "enemy", -60))
        faction.add_relation(FactionRelation("neutral1", "neutral", 0))

        allies = faction.get_allies()
        enemies = faction.get_enemies()

        assert len(allies) == 2
        assert len(enemies) == 1

    @pytest.mark.unit
    def test_add_goal(self, faction: Faction):
        """Test adding goals."""
        faction.add_goal("Expand trade routes")
        assert "Expand trade routes" in faction.goals

    @pytest.mark.unit
    def test_add_goal_limit(self, faction: Faction):
        """Test goal limit enforcement."""
        for i in range(10):
            faction.add_goal(f"Goal {i}")

        with pytest.raises(ValueError, match="Cannot have more than 10 goals"):
            faction.add_goal("Extra goal")

    @pytest.mark.unit
    def test_add_territory(self, faction: Faction):
        """Test adding territories."""
        faction.add_territory("location-1")
        faction.add_territory("location-2")
        faction.add_territory("location-1")  # Duplicate

        assert len(faction.territories) == 2

    @pytest.mark.unit
    def test_update_influence(self, faction: Faction):
        """Test updating influence."""
        faction.update_influence(20)
        assert faction.influence == 70

        faction.update_influence(-100)
        assert faction.influence == 0  # Capped at 0

        faction.update_influence(200)
        assert faction.influence == 100  # Capped at 100

    @pytest.mark.unit
    def test_power_rating(self, faction: Faction):
        """Test power rating calculation."""
        rating = faction.get_power_rating()
        # influence * 0.4 + military * 0.35 + economic * 0.25
        # 50 * 0.4 + 30 * 0.35 + 70 * 0.25 = 20 + 10.5 + 17.5 = 48
        assert rating == pytest.approx(48.0, rel=0.01)

    @pytest.mark.unit
    def test_factory_create_kingdom(self):
        """Test factory method for creating kingdom."""
        kingdom = Faction.create_kingdom(
            name="Kingdom of Test",
            alignment=FactionAlignment.LAWFUL_GOOD,
        )
        assert kingdom.faction_type == FactionType.KINGDOM
        assert kingdom.influence == 70

    @pytest.mark.unit
    def test_to_dict(self, faction: Faction):
        """Test dictionary serialization."""
        data = faction.to_dict()
        assert data["name"] == "Test Guild"
        assert data["faction_type"] == "guild"


class TestLocation:
    """Test suite for Location entity."""

    @pytest.fixture
    def location(self) -> Location:
        """Create a test Location instance."""
        return Location(
            name="Test City",
            description="A test city for unit testing",
            location_type=LocationType.CITY,
            climate=ClimateType.TEMPERATE,
            population=50000,
            accessibility=80,
            wealth_level=60,
        )

    @pytest.mark.unit
    def test_create_location(self, location: Location):
        """Test basic Location creation."""
        assert location.name == "Test City"
        assert location.location_type == LocationType.CITY
        assert location.population == 50000

    @pytest.mark.unit
    def test_location_validation_empty_name(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Location(name="")

    @pytest.mark.unit
    def test_location_validation_population(self):
        """Test population validation."""
        with pytest.raises(ValueError, match="Population cannot be negative"):
            Location(name="Test", population=-100)

    @pytest.mark.unit
    def test_location_validation_accessibility_range(self):
        """Test accessibility validation."""
        with pytest.raises(ValueError, match="Accessibility must be between"):
            Location(name="Test", accessibility=150)

    @pytest.mark.unit
    def test_add_child_location(self, location: Location):
        """Test adding child locations."""
        location.add_child_location("district-1")
        location.add_child_location("district-2")

        assert len(location.child_location_ids) == 2

    @pytest.mark.unit
    def test_cannot_add_self_as_child(self, location: Location):
        """Test that location cannot contain itself."""
        with pytest.raises(ValueError, match="cannot contain itself"):
            location.add_child_location(location.id)

    @pytest.mark.unit
    def test_set_parent_location(self, location: Location):
        """Test setting parent location."""
        location.set_parent_location("region-1")
        assert location.parent_location_id == "region-1"

    @pytest.mark.unit
    def test_cannot_set_self_as_parent(self, location: Location):
        """Test that location cannot be its own parent."""
        with pytest.raises(ValueError, match="cannot be its own parent"):
            location.set_parent_location(location.id)

    @pytest.mark.unit
    def test_add_connection(self, location: Location):
        """Test adding connections."""
        location.add_connection("other-city")
        assert "other-city" in location.connections

    @pytest.mark.unit
    def test_add_notable_feature(self, location: Location):
        """Test adding notable features."""
        location.add_notable_feature("Grand Cathedral")
        assert "Grand Cathedral" in location.notable_features

    @pytest.mark.unit
    def test_add_danger(self, location: Location):
        """Test adding dangers."""
        location.add_danger("Bandit raids")
        assert "Bandit raids" in location.dangers

    @pytest.mark.unit
    def test_is_settlement(self, location: Location):
        """Test settlement detection."""
        assert location.is_settlement() is True

        forest = Location(name="Dark Forest", location_type=LocationType.FOREST)
        assert forest.is_settlement() is False

    @pytest.mark.unit
    def test_is_natural(self, location: Location):
        """Test natural location detection."""
        assert location.is_natural() is False

        forest = Location(name="Dark Forest", location_type=LocationType.FOREST)
        assert forest.is_natural() is True

    @pytest.mark.unit
    def test_danger_level(self, location: Location):
        """Test danger level calculation."""
        assert location.get_danger_level() == "safe"

        location.add_danger("Thieves")
        location.add_danger("Disease")
        assert location.get_danger_level() == "cautionary"

    @pytest.mark.unit
    def test_factory_create_city(self):
        """Test factory method for creating city."""
        city = Location.create_city(
            name="New City",
            population=100000,
        )
        assert city.location_type == LocationType.CITY
        assert city.status == LocationStatus.THRIVING

    @pytest.mark.unit
    def test_factory_create_dungeon(self):
        """Test factory method for creating dungeon."""
        dungeon = Location.create_dungeon(
            name="Dark Dungeon",
            dangers=["traps", "undead"],
        )
        assert dungeon.location_type == LocationType.DUNGEON
        assert "traps" in dungeon.dangers

    @pytest.mark.unit
    def test_to_dict(self, location: Location):
        """Test dictionary serialization."""
        data = location.to_dict()
        assert data["name"] == "Test City"
        assert data["location_type"] == "city"


class TestHistoryEvent:
    """Test suite for HistoryEvent entity."""

    @pytest.fixture
    def event(self) -> HistoryEvent:
        """Create a test HistoryEvent instance."""
        return HistoryEvent(
            name="The Great War",
            description="A major conflict",
            event_type=EventType.WAR,
            significance=EventSignificance.MAJOR,
            outcome=EventOutcome.MIXED,
            date_description="Year 1000",
            faction_ids=["faction-1", "faction-2"],
        )

    @pytest.mark.unit
    def test_create_history_event(self, event: HistoryEvent):
        """Test basic HistoryEvent creation."""
        assert event.name == "The Great War"
        assert event.event_type == EventType.WAR
        assert event.significance == EventSignificance.MAJOR

    @pytest.mark.unit
    def test_history_event_validation_empty_name(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            HistoryEvent(name="", date_description="Year 1")

    @pytest.mark.unit
    def test_history_event_validation_no_date(self):
        """Test that missing date fails validation."""
        with pytest.raises(ValueError, match="must have a date"):
            HistoryEvent(name="Test Event", date_description="")

    @pytest.mark.unit
    def test_add_cause(self, event: HistoryEvent):
        """Test adding causes."""
        event.add_cause("Border disputes")
        assert "Border disputes" in event.causes

    @pytest.mark.unit
    def test_add_consequence(self, event: HistoryEvent):
        """Test adding consequences."""
        event.add_consequence("New kingdom formed")
        assert "New kingdom formed" in event.consequences

    @pytest.mark.unit
    def test_add_key_figure(self, event: HistoryEvent):
        """Test adding key figures."""
        event.add_key_figure("General Smith")
        assert "General Smith" in event.key_figures

    @pytest.mark.unit
    def test_add_preceding_event(self, event: HistoryEvent):
        """Test adding preceding events."""
        event.add_preceding_event("prior-event-id")
        assert "prior-event-id" in event.preceding_event_ids

    @pytest.mark.unit
    def test_cannot_precede_self(self, event: HistoryEvent):
        """Test that event cannot precede itself."""
        with pytest.raises(ValueError, match="cannot precede itself"):
            event.add_preceding_event(event.id)

    @pytest.mark.unit
    def test_add_following_event(self, event: HistoryEvent):
        """Test adding following events."""
        event.add_following_event("next-event-id")
        assert "next-event-id" in event.following_event_ids

    @pytest.mark.unit
    def test_cannot_follow_self(self, event: HistoryEvent):
        """Test that event cannot follow itself."""
        with pytest.raises(ValueError, match="cannot follow itself"):
            event.add_following_event(event.id)

    @pytest.mark.unit
    def test_circular_reference_prevention(self, event: HistoryEvent):
        """Test prevention of circular references."""
        event.add_preceding_event("other-event")

        with pytest.raises(ValueError, match="cannot be both"):
            event.add_following_event("other-event")

    @pytest.mark.unit
    def test_mark_as_secret(self, event: HistoryEvent):
        """Test marking event as secret."""
        assert event.is_secret is False
        event.mark_as_secret()
        assert event.is_secret is True

    @pytest.mark.unit
    def test_reveal_secret(self, event: HistoryEvent):
        """Test revealing secret event."""
        event.mark_as_secret()
        event.reveal_secret()
        assert event.is_secret is False

    @pytest.mark.unit
    def test_is_conflict(self, event: HistoryEvent):
        """Test conflict detection."""
        assert event.is_conflict() is True

        founding = HistoryEvent(
            name="City Founded",
            event_type=EventType.FOUNDING,
            date_description="Year 500",
        )
        assert founding.is_conflict() is False

    @pytest.mark.unit
    def test_is_world_changing(self, event: HistoryEvent):
        """Test world-changing detection."""
        assert event.is_world_changing() is False

        legendary = HistoryEvent(
            name="The Cataclysm",
            event_type=EventType.DISASTER,
            significance=EventSignificance.WORLD_CHANGING,
            date_description="Year 0",
        )
        assert legendary.is_world_changing() is True

    @pytest.mark.unit
    def test_update_narrative_importance(self, event: HistoryEvent):
        """Test updating narrative importance."""
        event.update_narrative_importance(80)
        assert event.narrative_importance == 80

    @pytest.mark.unit
    def test_update_narrative_importance_validation(self, event: HistoryEvent):
        """Test narrative importance validation."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            event.update_narrative_importance(150)

    @pytest.mark.unit
    def test_legendary_event_requires_importance(self):
        """Test that legendary events require minimum importance."""
        with pytest.raises(ValueError, match="at least 30"):
            HistoryEvent(
                name="Legendary Event",
                significance=EventSignificance.LEGENDARY,
                date_description="Year 1",
                narrative_importance=10,
            )

    @pytest.mark.unit
    def test_factory_create_war(self):
        """Test factory method for creating war."""
        war = HistoryEvent.create_war(
            name="Border War",
            description="A conflict",
            date_description="Year 800",
            faction_ids=["faction-a", "faction-b"],
        )
        assert war.event_type == EventType.WAR
        assert war.significance == EventSignificance.MAJOR

    @pytest.mark.unit
    def test_factory_create_founding(self):
        """Test factory method for creating founding."""
        founding = HistoryEvent.create_founding(
            name="City Founded",
            description="A new city",
            date_description="Year 100",
        )
        assert founding.event_type == EventType.FOUNDING
        assert founding.outcome == EventOutcome.POSITIVE

    @pytest.mark.unit
    def test_factory_create_disaster(self):
        """Test factory method for creating disaster."""
        disaster = HistoryEvent.create_disaster(
            name="Great Flood",
            description="Massive flooding",
            date_description="Year 500",
            location_ids=["coastal-city"],
        )
        assert disaster.event_type == EventType.DISASTER
        assert disaster.outcome == EventOutcome.NEGATIVE

    @pytest.mark.unit
    def test_to_dict(self, event: HistoryEvent):
        """Test dictionary serialization."""
        data = event.to_dict()
        assert data["name"] == "The Great War"
        assert data["event_type"] == "war"
        assert data["significance"] == "major"


class TestEntityBaseClass:
    """Test suite for base Entity functionality through concrete entities."""

    @pytest.mark.unit
    def test_entity_has_id(self):
        """Test that entities have auto-generated IDs."""
        setting = WorldSetting(name="Test World")
        assert setting.id is not None
        assert len(setting.id) > 0

    @pytest.mark.unit
    def test_entity_has_timestamps(self):
        """Test that entities have timestamps."""
        setting = WorldSetting(name="Test World")
        assert setting.created_at is not None
        assert setting.updated_at is not None

    @pytest.mark.unit
    def test_entity_has_version(self):
        """Test that entities have version tracking."""
        setting = WorldSetting(name="Test World")
        assert setting.version == 1

    @pytest.mark.unit
    def test_entity_touch_updates_version(self):
        """Test that touch() updates version and timestamp."""
        setting = WorldSetting(name="Test World")
        original_version = setting.version
        original_updated = setting.updated_at

        setting.add_theme("new theme")

        assert setting.version > original_version
        assert setting.updated_at >= original_updated

    @pytest.mark.unit
    def test_entity_equality(self):
        """Test entity equality based on ID."""
        setting1 = WorldSetting(name="World 1")
        setting2 = WorldSetting(name="World 2")

        # Different IDs means different entities
        assert setting1 != setting2

        # Same ID means equal (would need to manually set same ID for this)
        setting2_clone = WorldSetting(name="World 2 Clone")
        assert setting2 != setting2_clone

    @pytest.mark.unit
    def test_entity_usable_as_dict_key_via_id(self):
        """Test entity can be used in dicts via ID."""
        setting = WorldSetting(name="Test World")

        # Entities should be usable as dict keys via their ID
        entity_dict = {setting.id: setting}
        assert setting.id in entity_dict
        assert entity_dict[setting.id] == setting

    @pytest.mark.unit
    def test_entity_str_representation(self):
        """Test entity string representation."""
        setting = WorldSetting(name="Test World")
        str_repr = str(setting)

        assert "WorldSetting" in str_repr
        assert setting.id in str_repr
