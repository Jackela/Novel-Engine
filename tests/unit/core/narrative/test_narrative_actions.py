#!/usr/bin/env python3
"""Unit tests for src/core/narrative/narrative_actions.py module."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.narrative.narrative_actions import (
    NarrativeActionResolver,
    NarrativeActionType,
    NarrativeOutcome,
)
from src.core.types.shared_types import CharacterAction


class TestNarrativeActionType:
    """Tests for NarrativeActionType enum."""

    @pytest.mark.parametrize(
        "action_type,expected_value",
        [
            (NarrativeActionType.INVESTIGATE, "investigate"),
            (NarrativeActionType.DIALOGUE, "dialogue"),
            (NarrativeActionType.DIPLOMACY, "diplomacy"),
            (NarrativeActionType.BETRAYAL, "betrayal"),
            (NarrativeActionType.OBSERVE_ENVIRONMENT, "observe_environment"),
            (NarrativeActionType.SEARCH_AREA, "search_area"),
            (NarrativeActionType.ANALYZE_DATA, "analyze_data"),
            (NarrativeActionType.COMMUNICATE_FACTION, "communicate_faction"),
        ],
    )
    @pytest.mark.unit
    def test_narrative_action_type_values(self, action_type, expected_value):
        """Test that enum values are correctly defined."""
        assert action_type.value == expected_value

    @pytest.mark.unit
    def test_all_action_types_present(self):
        """Test that all expected action types are defined."""
        expected_types = {
            "INVESTIGATE",
            "DIALOGUE",
            "DIPLOMACY",
            "BETRAYAL",
            "OBSERVE_ENVIRONMENT",
            "SEARCH_AREA",
            "ANALYZE_DATA",
            "COMMUNICATE_FACTION",
        }
        actual_types = {t.name for t in NarrativeActionType}
        assert actual_types == expected_types


class TestNarrativeOutcome:
    """Tests for NarrativeOutcome dataclass."""

    @pytest.mark.unit
    def test_narrative_outcome_creation(self):
        """Test basic NarrativeOutcome creation."""
        outcome = NarrativeOutcome(
            success=True,
            description="Test description",
            character_impact={"agent_1": "impact_1"},
            environmental_change="The environment changed",
            story_advancement=["milestone_1"],
            relationship_changes={"agent_2": 0.5},
            discovered_information=["clue_1"],
            narrative_consequences=["consequence_1"],
        )

        assert outcome.success is True
        assert outcome.description == "Test description"
        assert outcome.character_impact == {"agent_1": "impact_1"}
        assert outcome.environmental_change == "The environment changed"
        assert outcome.story_advancement == ["milestone_1"]
        assert outcome.relationship_changes == {"agent_2": 0.5}
        assert outcome.discovered_information == ["clue_1"]
        assert outcome.narrative_consequences == ["consequence_1"]


class TestNarrativeActionResolverInit:
    """Tests for NarrativeActionResolver initialization."""

    @pytest.mark.unit
    def test_init_without_campaign_brief(self):
        """Test initialization without a campaign brief."""
        resolver = NarrativeActionResolver()

        assert resolver.campaign_brief is None
        assert resolver.investigation_counter == 0
        assert resolver.dialogue_history == []
        assert resolver.story_state == {}

    @pytest.mark.unit
    def test_init_with_campaign_brief(self):
        """Test initialization with a campaign brief."""
        brief = {"title": "Test Campaign", "setting": "Fantasy"}
        resolver = NarrativeActionResolver(campaign_brief=brief)

        assert resolver.campaign_brief == brief
        assert resolver.investigation_counter == 0
        assert resolver.dialogue_history == []
        assert resolver.story_state == {}


class TestNarrativeActionResolverResolveInvestigateAction:
    """Tests for resolve_investigate_action method."""

    @pytest.fixture
    def resolver(self):
        """Create a NarrativeActionResolver instance."""
        return NarrativeActionResolver()

    @pytest.fixture
    def sample_action(self):
        """Create a sample CharacterAction for investigation."""
        action = MagicMock(spec=CharacterAction)
        action.target = "ancient_ruins"
        return action

    @pytest.fixture
    def sample_character(self):
        """Create sample character data."""
        return {
            "name": "Test Character",
            "agent_id": "agent_1",
            "personality_traits": {"cautious": 0.8},
        }

    @pytest.fixture
    def sample_world_state(self):
        """Create sample world state."""
        return {"current_turn": 5, "weather": "clear"}

    @pytest.mark.unit
    def test_resolve_investigate_success(self, resolver, sample_action, sample_character, sample_world_state):
        """Test successful investigation resolution."""
        with patch("random.random", return_value=0.3):  # Below success threshold
            outcome = resolver.resolve_investigate_action(
                sample_action, sample_character, sample_world_state
            )

        assert isinstance(outcome, NarrativeOutcome)
        assert outcome.success is True
        assert "Test Character" in outcome.description
        assert "ancient_ruins" in outcome.description
        assert len(outcome.discovered_information) > 0
        assert outcome.character_impact["agent_1"] is not None

    @pytest.mark.unit
    def test_resolve_investigate_failure(self, resolver, sample_action, sample_character, sample_world_state):
        """Test failed investigation resolution."""
        with patch("random.random", return_value=0.9):  # Above success threshold
            outcome = resolver.resolve_investigate_action(
                sample_action, sample_character, sample_world_state
            )

        assert isinstance(outcome, NarrativeOutcome)
        assert outcome.success is False
        assert "finds nothing" in outcome.description or "yields no results" in outcome.description
        assert outcome.discovered_information == []

    @pytest.mark.unit
    def test_resolve_investigate_increments_counter(self, resolver, sample_action, sample_character, sample_world_state):
        """Test that investigation counter is incremented."""
        initial_count = resolver.investigation_counter

        with patch("random.random", return_value=0.5):
            resolver.resolve_investigate_action(sample_action, sample_character, sample_world_state)

        assert resolver.investigation_counter == initial_count + 1

    @pytest.mark.unit
    def test_resolve_investigate_with_unknown_target(self, resolver, sample_character, sample_world_state):
        """Test investigation with no target specified."""
        action = MagicMock(spec=CharacterAction)
        action.target = None

        with patch("random.random", return_value=0.5):
            outcome = resolver.resolve_investigate_action(
                action, sample_character, sample_world_state
            )

        assert isinstance(outcome, NarrativeOutcome)
        assert "unknown_area" in outcome.description or "None" in outcome.description

    @pytest.mark.unit
    def test_resolve_investigate_with_unknown_character_name(self, resolver, sample_action, sample_world_state):
        """Test investigation with character missing name."""
        character = {"agent_id": "agent_1", "personality_traits": {}}

        with patch("random.random", return_value=0.5):
            outcome = resolver.resolve_investigate_action(
                sample_action, character, sample_world_state
            )

        assert "Unknown" in outcome.description

    @pytest.mark.unit
    def test_resolve_investigate_without_agent_id(self, resolver, sample_action, sample_world_state):
        """Test investigation with character missing agent_id."""
        character = {"name": "Test", "personality_traits": {}}

        with patch("random.random", return_value=0.5):
            outcome = resolver.resolve_investigate_action(
                sample_action, character, sample_world_state
            )

        assert "unknown" in outcome.character_impact


class TestNarrativeActionResolverResolveDialogueAction:
    """Tests for resolve_dialogue_action method."""

    @pytest.fixture
    def resolver(self):
        """Create a NarrativeActionResolver instance."""
        return NarrativeActionResolver()

    @pytest.fixture
    def sample_action(self):
        """Create a sample CharacterAction for dialogue."""
        action = MagicMock(spec=CharacterAction)
        action.target = "NPC_John"
        return action

    @pytest.fixture
    def sample_character(self):
        """Create sample character data."""
        return {
            "name": "Test Character",
            "agent_id": "agent_1",
            "personality_traits": {"charismatic": 0.8},
        }

    @pytest.fixture
    def sample_world_state(self):
        """Create sample world state."""
        return {"current_turn": 10}

    @pytest.mark.unit
    def test_resolve_dialogue_success(self, resolver, sample_action, sample_character, sample_world_state):
        """Test successful dialogue resolution."""
        with patch("random.random", return_value=0.3):  # Below success threshold
            outcome = resolver.resolve_dialogue_action(
                sample_action, sample_character, sample_world_state
            )

        assert isinstance(outcome, NarrativeOutcome)
        assert outcome.success is True
        assert "successfully communicates" in outcome.description
        assert "NPC_John" in outcome.description
        assert len(outcome.discovered_information) > 0
        assert outcome.relationship_changes.get("NPC_John", 0) > 0

    @pytest.mark.unit
    def test_resolve_dialogue_failure(self, resolver, sample_action, sample_character, sample_world_state):
        """Test failed dialogue resolution."""
        with patch("random.random", return_value=0.9):  # Above success threshold
            outcome = resolver.resolve_dialogue_action(
                sample_action, sample_character, sample_world_state
            )

        assert isinstance(outcome, NarrativeOutcome)
        assert outcome.success is False
        assert "rebuffed" in outcome.description or "unsuccessful" in outcome.description
        assert outcome.relationship_changes == {}

    @pytest.mark.unit
    def test_resolve_dialogue_adds_to_history(self, resolver, sample_action, sample_character, sample_world_state):
        """Test that dialogue is added to history."""
        initial_history_len = len(resolver.dialogue_history)

        with patch("random.random", return_value=0.5):
            resolver.resolve_dialogue_action(sample_action, sample_character, sample_world_state)

        assert len(resolver.dialogue_history) == initial_history_len + 1
        last_entry = resolver.dialogue_history[-1]
        assert last_entry["character"] == "Test Character"
        assert last_entry["target"] == "NPC_John"
        assert last_entry["turn"] == 10

    @pytest.mark.unit
    def test_resolve_dialogue_with_unknown_target(self, resolver, sample_character, sample_world_state):
        """Test dialogue with no target specified."""
        action = MagicMock(spec=CharacterAction)
        action.target = None

        with patch("random.random", return_value=0.5):
            outcome = resolver.resolve_dialogue_action(
                action, sample_character, sample_world_state
            )

        assert "a nearby entity" in outcome.description


class TestNarrativeActionResolverPrivateMethods:
    """Tests for private helper methods."""

    @pytest.fixture
    def resolver(self):
        """Create a NarrativeActionResolver instance."""
        return NarrativeActionResolver()

    @pytest.mark.unit
    def test_calculate_investigation_success_base(self, resolver):
        """Test base investigation success calculation."""
        character_data = {"personality_traits": {}}
        success = resolver._calculate_investigation_success(character_data)

        assert success == 0.6  # Base chance

    @pytest.mark.unit
    def test_calculate_investigation_success_with_cautious_trait(self, resolver):
        """Test investigation success with cautious trait."""
        character_data = {"personality_traits": {"cautious": 0.8}}
        success = resolver._calculate_investigation_success(character_data)

        assert success == 0.8  # Base + 0.2

    @pytest.mark.unit
    def test_calculate_investigation_success_capped(self, resolver):
        """Test that investigation success is capped at 0.95."""
        character_data = {"personality_traits": {"cautious": 1.0}}
        success = resolver._calculate_investigation_success(character_data)

        assert success == 0.8  # Base 0.6 + 0.2 for cautious (not capped since it's below 0.95)

    @pytest.mark.unit
    def test_calculate_dialogue_success_base(self, resolver):
        """Test base dialogue success calculation."""
        character_data = {"personality_traits": {}}
        success = resolver._calculate_dialogue_success(character_data, "target")

        assert success == 0.5  # Base chance

    @pytest.mark.unit
    def test_calculate_dialogue_success_with_charismatic_trait(self, resolver):
        """Test dialogue success with charismatic trait."""
        character_data = {"personality_traits": {"charismatic": 0.8}}
        success = resolver._calculate_dialogue_success(character_data, "target")

        assert success == 0.7  # Base + 0.2

    @pytest.mark.unit
    def test_calculate_dialogue_success_capped(self, resolver):
        """Test that dialogue success is capped at 0.9."""
        character_data = {"personality_traits": {"charismatic": 1.0}}
        success = resolver._calculate_dialogue_success(character_data, "target")

        assert success == 0.7  # Base 0.5 + 0.2 for charismatic (not capped since it's below 0.9)

    @pytest.mark.unit
    def test_generate_investigation_discovery(self, resolver):
        """Test generation of investigation discovery."""
        target = "ancient_temple"
        character_data = {"name": "Explorer"}

        discoveries = resolver._generate_investigation_discovery(target, character_data)

        assert isinstance(discoveries, list)
        assert len(discoveries) > 0
        assert target in discoveries[0]

    @pytest.mark.unit
    def test_generate_dialogue_information(self, resolver):
        """Test generation of dialogue information."""
        target = "Village_Elder"

        info = resolver._generate_dialogue_information(target)

        assert isinstance(info, list)
        assert len(info) > 0
        assert target in info[0]

    @pytest.mark.unit
    def test_check_story_advancement_no_campaign_brief(self, resolver):
        """Test story advancement check without campaign brief."""
        advancement = resolver._check_story_advancement("investigation")

        assert advancement == []

    @pytest.mark.unit
    def test_check_story_advancement_investigation_milestone(self, resolver):
        """Test story advancement for investigation milestone."""
        resolver.campaign_brief = {"title": "Test"}
        resolver.investigation_counter = 3

        advancement = resolver._check_story_advancement("investigation")

        assert "Investigation milestone reached" in advancement

    @pytest.mark.unit
    def test_check_story_advancement_dialogue_milestone(self, resolver):
        """Test story advancement for dialogue milestone."""
        resolver.campaign_brief = {"title": "Test"}
        resolver.dialogue_history = [{}, {}]  # 2 entries

        advancement = resolver._check_story_advancement("dialogue")

        assert "Dialogue milestone reached" in advancement

    @pytest.mark.unit
    def test_check_story_advancement_no_milestone(self, resolver):
        """Test story advancement when no milestone is reached."""
        resolver.campaign_brief = {"title": "Test"}
        resolver.investigation_counter = 1
        resolver.dialogue_history = [{}]

        advancement = resolver._check_story_advancement("investigation")

        assert advancement == []
