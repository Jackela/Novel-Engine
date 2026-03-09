#!/usr/bin/env python3
"""Tests for SimulationSanityChecker.

Unit tests covering:
- Dead character has location check
- Faction no influence has territories check
- Circular location hierarchy check
- Orphaned entities check
- Duplicate faction relations check
- check_and_raise method
"""

from dataclasses import dataclass, field
from typing import List, Optional

import pytest

from src.contexts.world.application.services.simulation_sanity_checker import (
    SanityCheckError,
    SanityViolation,
    Severity,
    SimulationSanityChecker,
)

pytestmark = pytest.mark.unit


# ============================================================================
# Test Helpers (Minimal Mocks)
# ============================================================================


@dataclass
class MockCharacterID:
    """Mock CharacterID for testing."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class MockProfile:
    """Mock CharacterProfile for testing."""

    name: str


@dataclass
class MockCharacter:
    """Mock Character for testing."""

    character_id: MockCharacterID
    profile: MockProfile
    is_deceased: bool = False
    current_location_id: Optional[str] = None


@dataclass
class MockFactionRelation:
    """Mock FactionRelation for testing."""

    target_faction_id: str
    strength: int = 0


@dataclass
class MockFaction:
    """Mock Faction for testing."""

    id: str
    name: str
    influence: int = 50
    territories: List[str] = field(default_factory=list)
    relations: List[MockFactionRelation] = field(default_factory=list)


@dataclass
class MockLocation:
    """Mock Location for testing."""

    id: str
    name: str
    parent_location_id: Optional[str] = None


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def checker() -> SimulationSanityChecker:
    """Create a fresh sanity checker."""
    return SimulationSanityChecker()


@pytest.fixture
def healthy_characters() -> List[MockCharacter]:
    """Create healthy characters with no violations."""
    return [
        MockCharacter(
            character_id=MockCharacterID("char-1"),
            profile=MockProfile(name="Alice"),
            is_deceased=False,
            current_location_id="loc-1",
        ),
        MockCharacter(
            character_id=MockCharacterID("char-2"),
            profile=MockProfile(name="Bob"),
            is_deceased=False,
            current_location_id="loc-2",
        ),
    ]


@pytest.fixture
def healthy_factions() -> List[MockFaction]:
    """Create healthy factions with no violations."""
    return [
        MockFaction(
            id="faction-1",
            name="Kingdom",
            influence=70,
            territories=["loc-1", "loc-2"],
            relations=[MockFactionRelation(target_faction_id="faction-2")],
        ),
        MockFaction(
            id="faction-2",
            name="Guild",
            influence=40,
            territories=["loc-3"],
            relations=[MockFactionRelation(target_faction_id="faction-1")],
        ),
    ]


@pytest.fixture
def healthy_locations() -> List[MockLocation]:
    """Create healthy locations with no violations."""
    return [
        MockLocation(id="loc-1", name="Capital", parent_location_id=None),
        MockLocation(id="loc-2", name="Town", parent_location_id="loc-1"),
        MockLocation(id="loc-3", name="Village", parent_location_id="loc-1"),
    ]


# ============================================================================
# Test Severity Enum
# ============================================================================


class TestSeverity:
    """Tests for Severity enum."""

    def test_warning_value(self) -> None:
        """Should have warning value."""
        assert Severity.WARNING.value == "warning"

    def test_error_value(self) -> None:
        """Should have error value."""
        assert Severity.ERROR.value == "error"


# ============================================================================
# Test SanityViolation
# ============================================================================


class TestSanityViolation:
    """Tests for SanityViolation dataclass."""

    def test_create_violation(self) -> None:
        """Should create violation with all fields."""
        violation = SanityViolation(
            rule_name="test_rule",
            severity=Severity.ERROR,
            message="Test message",
            affected_ids=["id-1", "id-2"],
        )

        assert violation.rule_name == "test_rule"
        assert violation.severity == Severity.ERROR
        assert violation.message == "Test message"
        assert violation.affected_ids == ["id-1", "id-2"]

    def test_default_affected_ids(self) -> None:
        """Should default to empty list for affected_ids."""
        violation = SanityViolation(
            rule_name="test_rule",
            severity=Severity.WARNING,
            message="Test",
        )

        assert violation.affected_ids == []

    def test_to_dict(self) -> None:
        """Should convert to dictionary."""
        violation = SanityViolation(
            rule_name="test_rule",
            severity=Severity.ERROR,
            message="Test message",
            affected_ids=["id-1"],
        )

        result = violation.to_dict()

        assert result["rule_name"] == "test_rule"
        assert result["severity"] == "error"
        assert result["message"] == "Test message"
        assert result["affected_ids"] == ["id-1"]


# ============================================================================
# Test SanityCheckError
# ============================================================================


class TestSanityCheckError:
    """Tests for SanityCheckError exception."""

    def test_create_with_violations(self) -> None:
        """Should create exception with violations."""
        violations = [
            SanityViolation(
                rule_name="rule1",
                severity=Severity.ERROR,
                message="Error 1",
            ),
            SanityViolation(
                rule_name="rule2",
                severity=Severity.ERROR,
                message="Error 2",
            ),
        ]

        error = SanityCheckError(violations)

        assert error.violations == violations
        assert "Error 1" in str(error)
        assert "Error 2" in str(error)


# ============================================================================
# Test Empty Check
# ============================================================================


class TestEmptyCheck:
    """Tests for checking with no entities."""

    def test_empty_check_returns_empty(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should return empty list when no entities."""
        result = checker.check()

        assert result.is_ok
        assert result.unwrap() == []

    def test_empty_check_and_raise_no_error(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not raise when no entities."""
        checker.check_and_raise()  # Should not raise


# ============================================================================
# Test Dead Character Has Location Check
# ============================================================================


class TestDeadCharacterHasLocation:
    """Tests for dead_character_has_location rule."""

    def test_no_violation_when_alive(
        self,
        checker: SimulationSanityChecker,
        healthy_locations: List[MockLocation],
    ) -> None:
        """Should not flag alive characters with location."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
                is_deceased=False,
                current_location_id="loc-1",
            ),
        ]
        checker.set_entities(characters=characters, locations=healthy_locations)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "dead_character_has_location"
        ]
        assert len(violations) == 0

    def test_no_violation_when_dead_no_location(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag dead characters without location."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
                is_deceased=True,
                current_location_id=None,
            ),
        ]
        checker.set_entities(characters=characters)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "dead_character_has_location"
        ]
        assert len(violations) == 0

    def test_violation_when_dead_with_location(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag dead characters with location as ERROR."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
                is_deceased=True,
                current_location_id="loc-1",
            ),
        ]
        checker.set_entities(characters=characters)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "dead_character_has_location"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR
        assert "char-1" in violations[0].affected_ids

    def test_multiple_dead_with_locations(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag multiple dead characters with locations."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
                is_deceased=True,
                current_location_id="loc-1",
            ),
            MockCharacter(
                character_id=MockCharacterID("char-2"),
                profile=MockProfile(name="Bob"),
                is_deceased=True,
                current_location_id="loc-2",
            ),
        ]
        checker.set_entities(characters=characters)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "dead_character_has_location"
        ]
        assert len(violations) == 2


# ============================================================================
# Test Faction No Influence Has Territories
# ============================================================================


class TestFactionNoInfluenceHasTerritories:
    """Tests for faction_no_influence_has_territories rule."""

    def test_no_violation_when_has_influence(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag factions with influence."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Kingdom",
                influence=50,
                territories=["loc-1"],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v
            for v in result.unwrap()
            if v.rule_name == "faction_no_influence_has_territories"
        ]
        assert len(violations) == 0

    def test_no_violation_when_no_influence_no_territories(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag factions with no influence and no territories."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Collapsed Guild",
                influence=0,
                territories=[],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v
            for v in result.unwrap()
            if v.rule_name == "faction_no_influence_has_territories"
        ]
        assert len(violations) == 0

    def test_violation_when_no_influence_has_territories(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag factions with no influence but territories as WARNING."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Collapsed Kingdom",
                influence=0,
                territories=["loc-1", "loc-2"],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v
            for v in result.unwrap()
            if v.rule_name == "faction_no_influence_has_territories"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_multiple_factions_violations(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag multiple factions with violations."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Kingdom A",
                influence=0,
                territories=["loc-1"],
            ),
            MockFaction(
                id="faction-2",
                name="Kingdom B",
                influence=0,
                territories=["loc-2", "loc-3"],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v
            for v in result.unwrap()
            if v.rule_name == "faction_no_influence_has_territories"
        ]
        assert len(violations) == 2


# ============================================================================
# Test Circular Location Hierarchy
# ============================================================================


class TestCircularLocationHierarchy:
    """Tests for circular_location_hierarchy rule."""

    def test_no_violation_when_no_hierarchy(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag flat hierarchy."""
        locations = [
            MockLocation(id="loc-1", name="A", parent_location_id=None),
            MockLocation(id="loc-2", name="B", parent_location_id=None),
        ]
        checker.set_entities(locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "circular_location_hierarchy"
        ]
        assert len(violations) == 0

    def test_no_violation_when_valid_hierarchy(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag valid hierarchy."""
        locations = [
            MockLocation(id="loc-1", name="Root", parent_location_id=None),
            MockLocation(id="loc-2", name="Child", parent_location_id="loc-1"),
            MockLocation(id="loc-3", name="Grandchild", parent_location_id="loc-2"),
        ]
        checker.set_entities(locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "circular_location_hierarchy"
        ]
        assert len(violations) == 0

    def test_violation_when_direct_cycle(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag direct cycle (A -> B -> A)."""
        locations = [
            MockLocation(id="loc-1", name="A", parent_location_id="loc-2"),
            MockLocation(id="loc-2", name="B", parent_location_id="loc-1"),
        ]
        checker.set_entities(locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "circular_location_hierarchy"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    def test_violation_when_self_reference(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag self-reference cycle (A -> A)."""
        locations = [
            MockLocation(id="loc-1", name="A", parent_location_id="loc-1"),
        ]
        checker.set_entities(locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "circular_location_hierarchy"
        ]
        assert len(violations) == 1

    def test_violation_when_longer_cycle(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag longer cycle (A -> B -> C -> A)."""
        locations = [
            MockLocation(id="loc-1", name="A", parent_location_id="loc-3"),
            MockLocation(id="loc-2", name="B", parent_location_id="loc-1"),
            MockLocation(id="loc-3", name="C", parent_location_id="loc-2"),
        ]
        checker.set_entities(locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "circular_location_hierarchy"
        ]
        assert len(violations) == 1


# ============================================================================
# Test Orphaned Entities
# ============================================================================


class TestOrphanedEntities:
    """Tests for orphaned_entities rule."""

    def test_no_violation_when_valid_references(
        self,
        checker: SimulationSanityChecker,
        healthy_characters: List[MockCharacter],
        healthy_locations: List[MockLocation],
    ) -> None:
        """Should not flag valid references."""
        checker.set_entities(characters=healthy_characters, locations=healthy_locations)

        result = checker.check()

        assert result.is_ok
        violations = [v for v in result.unwrap() if v.rule_name == "orphaned_entities"]
        assert len(violations) == 0

    def test_violation_when_location_parent_missing(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag location with non-existent parent."""
        locations = [
            MockLocation(id="loc-1", name="Child", parent_location_id="nonexistent"),
        ]
        checker.set_entities(locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [v for v in result.unwrap() if v.rule_name == "orphaned_entities"]
        assert len(violations) == 1
        assert violations[0].severity == Severity.WARNING

    def test_violation_when_character_in_missing_location(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag character in non-existent location."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
                current_location_id="nonexistent",
            ),
        ]
        locations = [
            MockLocation(id="loc-1", name="Real Location"),
        ]
        checker.set_entities(characters=characters, locations=locations)

        result = checker.check()

        assert result.is_ok
        violations = [v for v in result.unwrap() if v.rule_name == "orphaned_entities"]
        assert len(violations) == 1

    def test_no_violation_when_character_has_no_location(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag character with no location."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
                current_location_id=None,
            ),
        ]
        checker.set_entities(characters=characters)

        result = checker.check()

        assert result.is_ok
        violations = [v for v in result.unwrap() if v.rule_name == "orphaned_entities"]
        assert len(violations) == 0


# ============================================================================
# Test Duplicate Faction Relations
# ============================================================================


class TestDuplicateFactionRelations:
    """Tests for duplicate_faction_relations rule."""

    def test_no_violation_when_unique_relations(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag unique relations."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Kingdom",
                relations=[
                    MockFactionRelation(target_faction_id="faction-2"),
                    MockFactionRelation(target_faction_id="faction-3"),
                ],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "duplicate_faction_relations"
        ]
        assert len(violations) == 0

    def test_no_violation_when_no_relations(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not flag factions with no relations."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Isolationists",
                relations=[],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "duplicate_faction_relations"
        ]
        assert len(violations) == 0

    def test_violation_when_duplicate_relations(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag duplicate relations as ERROR."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Kingdom",
                relations=[
                    MockFactionRelation(target_faction_id="faction-2"),
                    MockFactionRelation(target_faction_id="faction-2"),  # Duplicate
                ],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "duplicate_faction_relations"
        ]
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    def test_violation_when_multiple_duplicates(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should flag multiple duplicate targets."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Kingdom",
                relations=[
                    MockFactionRelation(target_faction_id="faction-2"),
                    MockFactionRelation(target_faction_id="faction-2"),
                    MockFactionRelation(target_faction_id="faction-3"),
                    MockFactionRelation(target_faction_id="faction-3"),
                ],
            ),
        ]
        checker.set_entities(factions=factions)

        result = checker.check()

        assert result.is_ok
        violations = [
            v for v in result.unwrap() if v.rule_name == "duplicate_faction_relations"
        ]
        assert len(violations) == 1
        # Should report both duplicate targets
        assert "faction-2" in violations[0].message
        assert "faction-3" in violations[0].message


# ============================================================================
# Test check_and_raise
# ============================================================================


class TestCheckAndRaise:
    """Tests for check_and_raise method."""

    def test_no_raise_when_no_violations(
        self,
        checker: SimulationSanityChecker,
        healthy_characters: List[MockCharacter],
        healthy_factions: List[MockFaction],
        healthy_locations: List[MockLocation],
    ) -> None:
        """Should not raise when healthy."""
        checker.set_entities(
            characters=healthy_characters,
            factions=healthy_factions,
            locations=healthy_locations,
        )

        checker.check_and_raise()  # Should not raise

    def test_no_raise_when_only_warnings(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should not raise when only WARNING violations."""
        factions = [
            MockFaction(
                id="faction-1",
                name="Kingdom",
                influence=0,
                territories=["loc-1"],
            ),
        ]
        checker.set_entities(factions=factions)

        checker.check_and_raise()  # Should not raise

    def test_raises_when_error_violations(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should raise when ERROR violations exist."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Ghost"),
                is_deceased=True,
                current_location_id="loc-1",
            ),
        ]
        checker.set_entities(characters=characters)

        with pytest.raises(SanityCheckError) as exc_info:
            checker.check_and_raise()

        assert len(exc_info.value.violations) == 1
        assert exc_info.value.violations[0].severity == Severity.ERROR

    def test_raises_with_multiple_errors(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should raise with all ERROR violations."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Ghost 1"),
                is_deceased=True,
                current_location_id="loc-1",
            ),
            MockCharacter(
                character_id=MockCharacterID("char-2"),
                profile=MockProfile(name="Ghost 2"),
                is_deceased=True,
                current_location_id="loc-2",
            ),
        ]
        checker.set_entities(characters=characters)

        with pytest.raises(SanityCheckError) as exc_info:
            checker.check_and_raise()

        assert len(exc_info.value.violations) == 2


# ============================================================================
# Test set_entities
# ============================================================================


class TestSetEntities:
    """Tests for set_entities method."""

    def test_set_characters(self, checker: SimulationSanityChecker) -> None:
        """Should update character list."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
            ),
        ]

        checker.set_entities(characters=characters)

        assert checker._characters == characters

    def test_set_factions(self, checker: SimulationSanityChecker) -> None:
        """Should update faction list."""
        factions = [
            MockFaction(id="faction-1", name="Test"),
        ]

        checker.set_entities(factions=factions)

        assert checker._factions == factions

    def test_set_locations(self, checker: SimulationSanityChecker) -> None:
        """Should update location list."""
        locations = [
            MockLocation(id="loc-1", name="Test"),
        ]

        checker.set_entities(locations=locations)

        assert checker._locations == locations

    def test_set_all_entities(self, checker: SimulationSanityChecker) -> None:
        """Should update all entity lists."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
            ),
        ]
        factions = [
            MockFaction(id="faction-1", name="Test"),
        ]
        locations = [
            MockLocation(id="loc-1", name="Test"),
        ]

        checker.set_entities(
            characters=characters, factions=factions, locations=locations
        )

        assert checker._characters == characters
        assert checker._factions == factions
        assert checker._locations == locations

    def test_partial_update(self, checker: SimulationSanityChecker) -> None:
        """Should only update specified entities."""
        initial_chars = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Alice"),
            ),
        ]
        checker.set_entities(characters=initial_chars)

        new_factions = [
            MockFaction(id="faction-1", name="Test"),
        ]
        checker.set_entities(factions=new_factions)

        # Characters should remain unchanged
        assert checker._characters == initial_chars
        assert checker._factions == new_factions


# ============================================================================
# Test Combined Scenarios
# ============================================================================


class TestCombinedScenarios:
    """Tests for combined violation scenarios."""

    def test_multiple_violation_types(
        self,
        checker: SimulationSanityChecker,
    ) -> None:
        """Should detect multiple types of violations."""
        characters = [
            MockCharacter(
                character_id=MockCharacterID("char-1"),
                profile=MockProfile(name="Ghost"),
                is_deceased=True,
                current_location_id="loc-1",
            ),
        ]
        factions = [
            MockFaction(
                id="faction-1",
                name="Collapsed",
                influence=0,
                territories=["loc-1"],
            ),
        ]
        locations = [
            MockLocation(id="loc-1", name="Cycle", parent_location_id="loc-1"),
        ]
        checker.set_entities(
            characters=characters, factions=factions, locations=locations
        )

        result = checker.check()

        # Should have at least 3 violations (one from each rule)
        assert result.is_ok
        violations = result.unwrap()
        assert len(violations) >= 3

        # Check each type is present
        rule_names = {v.rule_name for v in violations}
        assert "dead_character_has_location" in rule_names
        assert "faction_no_influence_has_territories" in rule_names
        assert "circular_location_hierarchy" in rule_names

    def test_healthy_world(
        self,
        checker: SimulationSanityChecker,
        healthy_characters: List[MockCharacter],
        healthy_factions: List[MockFaction],
        healthy_locations: List[MockLocation],
    ) -> None:
        """Should find no violations in healthy world."""
        checker.set_entities(
            characters=healthy_characters,
            factions=healthy_factions,
            locations=healthy_locations,
        )

        result = checker.check()

        assert result.is_ok
        assert len(result.unwrap()) == 0
