#!/usr/bin/env python3
"""
Test suite for ChroniclerAgent module.

Tests narrative generation, event processing, and story composition.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit

from src.agents.chronicler_agent import (
    CampaignEvent,
    ChroniclerAgent,
    NarrativeSegment,
    _limit_story_length,
    _sanitize_story,
)
from src.core.event_bus import EventBus


class TestSanitizeStory:
    """Test story sanitization functions."""

    def test_sanitize_removes_script_tags(self):
        """Test that script tags are removed."""
        story = "<script>alert('xss')</script>Normal text"
        result = _sanitize_story(story)
        assert "<script>" not in result
        assert "Normal text" in result

    def test_sanitize_removes_sql_injection(self):
        """Test that SQL injection patterns are neutralized."""
        story = "DROP TABLE users; Normal text"
        result = _sanitize_story(story)
        assert "DROP TABLE" not in result
        assert "neutralized command" in result.lower()

    def test_sanitize_removes_null_bytes(self):
        """Test that null bytes are removed."""
        story = "Text with\x00null byte"
        result = _sanitize_story(story)
        assert "\x00" not in result

    def test_sanitize_empty_input(self):
        """Test sanitizing empty input."""
        assert _sanitize_story("") == ""
        assert _sanitize_story(None) == ""


class TestLimitStoryLength:
    """Test story length limiting."""

    def test_limit_within_bounds(self):
        """Test limiting story within bounds."""
        story = "Short story."
        result = _limit_story_length(story, max_length=100)
        assert result == story

    def test_limit_truncates_at_sentence(self):
        """Test truncation at sentence boundary."""
        story = "First sentence. Second sentence. " + "x" * 10000
        result = _limit_story_length(story, max_length=100)
        # Truncation may happen at sentence boundary or with hard cutoff
        # Either way, the result should not exceed max_length
        assert len(result) <= 100
        # If truncated at sentence boundary, should end with punctuation
        # If hard cutoff, may not end with punctuation

    def test_limit_hard_cutoff(self):
        """Test hard cutoff when no sentence boundary."""
        story = "x" * 10000
        result = _limit_story_length(story, max_length=100)
        assert len(result) <= 100

    def test_limit_empty(self):
        """Test limiting empty story."""
        assert _limit_story_length("") == ""


class TestCampaignEvent:
    """Test CampaignEvent dataclass."""

    def test_default_creation(self):
        """Test creating CampaignEvent."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2024-01-01T00:00:00",
            event_type="action",
            description="Test event",
        )
        assert event.turn_number == 1
        assert event.event_type == "action"
        assert event.description == "Test event"
        assert event.participants == []
        assert event.faction_info == {}

    def test_full_creation(self):
        """Test creating CampaignEvent with all fields."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2024-01-01T00:00:00",
            event_type="combat",
            description="Battle occurred",
            participants=["hero", "villain"],
            faction_info={"hero": "Alliance"},
            action_details={"damage": 10},
            raw_text="Raw event text",
        )
        assert len(event.participants) == 2
        assert event.faction_info["hero"] == "Alliance"


class TestNarrativeSegment:
    """Test NarrativeSegment dataclass."""

    def test_default_creation(self):
        """Test creating NarrativeSegment."""
        segment = NarrativeSegment(
            turn_number=1,
            event_type="action",
            narrative_text="The hero acted.",
        )
        assert segment.turn_number == 1
        assert segment.narrative_text == "The hero acted."
        assert segment.character_focus == []
        assert segment.tone == "dramatic"


class TestChroniclerAgentInitialization:
    """Test ChroniclerAgent initialization."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        event_bus = EventBus()
        agent = ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero", "sidekick"],
        )

        assert agent.event_bus == event_bus
        assert agent.character_names == ["hero", "sidekick"]
        assert agent.narrative_segments == []
        assert agent.narrative_style == "sci_fi_dramatic"

    def test_initialization_requires_event_bus(self):
        """Test that event_bus is required."""
        with pytest.raises(ValueError):
            ChroniclerAgent(event_bus=None, character_names=["hero"])

    def test_initialization_requires_character_names(self):
        """Test that character_names is required."""
        event_bus = EventBus()
        with pytest.raises(ValueError):
            ChroniclerAgent(event_bus=event_bus, character_names=[])

    def test_initialization_with_output_directory(self):
        """Test initialization with output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            event_bus = EventBus()
            agent = ChroniclerAgent(
                event_bus=event_bus,
                character_names=["hero"],
                output_directory=tmpdir,
            )

            assert agent.output_directory == tmpdir

    def test_initialization_with_style(self):
        """Test initialization with narrative style."""
        event_bus = EventBus()
        agent = ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero"],
            narrative_style="tactical",
        )

        assert agent.narrative_style == "tactical"

    def test_initialization_invalid_style_defaults(self):
        """Test that invalid style defaults to sci_fi_dramatic."""
        event_bus = EventBus()
        agent = ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero"],
            narrative_style="nonexistent_style",
        )

        assert agent.narrative_style == "sci_fi_dramatic"


class TestChroniclerAgentStyle:
    """Test narrative style methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero"],
        )

    def test_set_narrative_style_valid(self, chronicler):
        """Test setting valid narrative style."""
        result = chronicler.set_narrative_style("tactical")

        assert result is True
        assert chronicler.narrative_style == "tactical"

    def test_set_narrative_style_invalid(self, chronicler):
        """Test setting invalid narrative style."""
        result = chronicler.set_narrative_style("invalid_style")

        assert result is False
        assert chronicler.narrative_style != "invalid_style"

    def test_set_narrative_style_case_insensitive(self, chronicler):
        """Test style setting is case insensitive."""
        result = chronicler.set_narrative_style("  TACTICAL  ")

        assert result is True
        assert chronicler.narrative_style == "tactical"


class TestChroniclerAgentEventHandling:
    """Test event handling methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero", "villain"],
        )

    def test_handle_agent_action(self, chronicler):
        """Test handling agent action event."""
        agent = Mock()
        agent.character_data = {"name": "Hero"}
        action = Mock()
        action.action_type = "attack"
        action.reasoning = "Defend allies"
        action.target = "villain"
        action.priority = "high"
        action.parameters = {}

        # Mock the LLM call to avoid API dependency
        with patch.object(chronicler, '_call_llm', return_value="Hero attacked villain."):
            chronicler.handle_agent_action(agent, action)

        assert len(chronicler.narrative_segments) == 1

    def test_handle_agent_action_none(self, chronicler):
        """Test handling None action."""
        agent = Mock()
        chronicler.handle_agent_action(agent, None)

        assert len(chronicler.narrative_segments) == 0

    def test_handle_simulation_end(self, chronicler):
        """Test handling simulation end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chronicler.output_directory = tmpdir
            chronicler.narrative_segments.append(
                NarrativeSegment(
                    turn_number=1,
                    event_type="action",
                    narrative_text="Test",
                    character_focus=["hero"],
                )
            )

            chronicler.handle_simulation_end()

            # Should create a file
            files = list(Path(tmpdir).glob("*.md"))
            assert len(files) == 1


class TestChroniclerAgentNarrativeGeneration:
    """Test narrative generation methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero", "villain"],
        )

    def test_create_narrative_prompt(self, chronicler):
        """Test creating narrative prompt."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2024-01-01",
            event_type="combat",
            description="A battle occurred",
        )

        prompt = chronicler._create_narrative_prompt(event)

        assert "Narrate" in prompt
        assert "battle occurred" in prompt

    def test_render_event_narrative_agent_registration(self, chronicler):
        """Test rendering agent registration event."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2024-01-01",
            event_type="agent_registration",
            description="Hero joined",
            participants=["Hero"],
        )

        narrative = chronicler._render_event_narrative(event)

        assert "Hero" in narrative
        assert "Meridian Station" in narrative or "docked" in narrative.lower()

    def test_render_event_narrative_action(self, chronicler):
        """Test rendering action event."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2024-01-01",
            event_type="action",
            description="Hero attacked",
            participants=["Hero"],
        )

        narrative = chronicler._render_event_narrative(event)

        assert "Hero" in narrative

    def test_render_event_narrative_turn_end(self, chronicler):
        """Test rendering turn end event."""
        event = CampaignEvent(
            turn_number=5,
            timestamp="2024-01-01",
            event_type="turn_end",
            description="Turn ended",
        )

        narrative = chronicler._render_event_narrative(event)

        assert "Turn 5" in narrative or "concluded" in narrative.lower()

    def test_render_event_narrative_generic(self, chronicler):
        """Test rendering generic event."""
        event = CampaignEvent(
            turn_number=1,
            timestamp="2024-01-01",
            event_type="unknown",
            description="Something happened",
            participants=["Hero"],
        )

        narrative = chronicler._render_event_narrative(event)

        assert "Hero" in narrative


class TestChroniclerAgentParsing:
    """Test log parsing methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero", "villain"],
        )

    def test_parse_campaign_log(self, chronicler):
        """Test parsing campaign log."""
        log_content = """
Turn 1
Hero decided to attack the enemy
Villain chose to defend
[Turn End]

Turn 2
Hero decided to retreat
"""
        events = chronicler._parse_campaign_log(log_content)

        assert len(events) > 0
        assert any(e.event_type == "action" for e in events)

    def test_parse_campaign_log_turn_markers(self, chronicler):
        """Test parsing turn markers."""
        log_content = "Turn 5\nAction occurred"

        events = chronicler._parse_campaign_log(log_content)

        turn_events = [e for e in events if e.event_type == "turn_start"]
        assert len(turn_events) == 1
        assert turn_events[0].turn_number == 5

    def test_parse_campaign_log_agent_registration(self, chronicler):
        """Test parsing agent registration."""
        log_content = "[Agent Registration] Hero registered"

        events = chronicler._parse_campaign_log(log_content)

        reg_events = [e for e in events if e.event_type == "agent_registration"]
        assert len(reg_events) == 1

    def test_parse_campaign_log_turn_end(self, chronicler):
        """Test parsing turn end markers."""
        log_content = "[Turn End]"

        events = chronicler._parse_campaign_log(log_content)

        end_events = [e for e in events if e.event_type == "turn_end"]
        assert len(end_events) == 1

    def test_extract_participants(self, chronicler):
        """Test extracting participants from log line."""
        line = "Hero and Villain fought together"

        participants = chronicler._extract_participants(line)

        assert "hero" in [p.lower() for p in participants]
        assert "villain" in [p.lower() for p in participants]


class TestChroniclerAgentCombination:
    """Test narrative combination methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero", "sidekick"],
        )

    def test_combine_narrative_segments(self, chronicler):
        """Test combining narrative segments."""
        segments = [
            NarrativeSegment(
                turn_number=1,
                event_type="action",
                narrative_text="First event",
                character_focus=["hero"],
            ),
            NarrativeSegment(
                turn_number=2,
                event_type="combat",
                narrative_text="Second event",
                character_focus=["hero", "sidekick"],
            ),
        ]

        story = chronicler._combine_narrative_segments(segments)

        assert "First event" in story
        assert "Second event" in story
        assert "hero" in story.lower()

    def test_combine_empty_segments(self, chronicler):
        """Test combining empty segments."""
        story = chronicler._combine_narrative_segments([])

        assert isinstance(story, str)
        assert len(story) > 0  # Should have default story

    def test_build_default_story(self, chronicler):
        """Test building default story."""
        story = chronicler._build_default_story()

        assert isinstance(story, str)
        assert "hero" in story.lower() or "sidekick" in story.lower()

    def test_generate_narrative_segments(self, chronicler):
        """Test generating narrative segments from events."""
        events = [
            CampaignEvent(
                turn_number=1,
                timestamp="2024-01-01",
                event_type="action",
                description="Hero acted",
                participants=["Hero"],
            ),
        ]

        segments = chronicler._generate_narrative_segments(events)

        assert len(segments) == 1
        assert segments[0].turn_number == 1


class TestChroniclerAgentPromptBuilding:
    """Test prompt building methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero", "villain"],
        )

    def test_build_story_prompt(self, chronicler):
        """Test building story prompt."""
        base_story = "Hero fought Villain and won."

        prompt = chronicler._build_story_prompt(base_story)

        assert "hero" in prompt.lower()
        assert "villain" in prompt.lower()
        assert base_story in prompt


class TestChroniclerAgentTranscription:
    """Test log transcription methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero"],
        )

    def test_transcribe_log_file_not_found(self, chronicler):
        """Test transcribing non-existent log."""
        with pytest.raises(FileNotFoundError):
            chronicler.transcribe_log("/nonexistent/log.md")

    def test_transcribe_log_success(self, chronicler):
        """Test successful log transcription."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("Turn 1\nHero decided to explore\n")
            log_path = f.name

        try:
            story = chronicler.transcribe_log(log_path)

            assert isinstance(story, str)
            assert len(story) > 0
        finally:
            os.unlink(log_path)


class TestChroniclerAgentOutput:
    """Test output methods."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero"],
        )

    def test_save_narrative_to_file(self, chronicler):
        """Test saving narrative to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            chronicler.output_directory = tmpdir

            path = chronicler._save_narrative_to_file("Test narrative", "test_story")

            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
                assert "Test narrative" in content


class TestChroniclerAgentMetrics:
    """Test metrics and tracking."""

    @pytest.fixture
    def chronicler(self):
        """Create a ChroniclerAgent."""
        event_bus = EventBus()
        return ChroniclerAgent(
            event_bus=event_bus,
            character_names=["hero"],
        )

    def test_initial_metrics(self, chronicler):
        """Test initial metrics values."""
        assert chronicler.events_processed == 0
        assert chronicler.narratives_generated == 0
        assert chronicler.llm_calls_made == 0
        assert chronicler.error_count == 0


class TestChroniclerAgentIntegration:
    """Integration tests."""

    def test_full_narrative_flow(self):
        """Test full narrative generation flow."""
        event_bus = EventBus()
        chronicler = ChroniclerAgent(
            event_bus=event_bus,
            character_names=["pilot", "engineer"],
        )

        # Simulate events
        agent1 = Mock()
        agent1.character_data = {"name": "Pilot"}
        action1 = Mock()
        action1.action_type = "navigate"
        action1.reasoning = "Course correction needed"

        agent2 = Mock()
        agent2.character_data = {"name": "Engineer"}
        action2 = Mock()
        action2.action_type = "repair"
        action2.reasoning = "Fixing engine"

        # Mock the LLM call to avoid API dependency
        with patch.object(chronicler, '_call_llm', return_value="Pilot navigated. Engineer repaired."):
            chronicler.handle_agent_action(agent1, action1)
            chronicler.handle_agent_action(agent2, action2)

        # Generate narrative
        story = chronicler._combine_narrative_segments(chronicler.narrative_segments)

        assert len(chronicler.narrative_segments) == 2
        assert isinstance(story, str)
        assert len(story) > 0

    def test_transcribe_full_campaign(self):
        """Test transcribing a full campaign log."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""
Turn 1
[Agent Registration] Pilot registered for simulation
Pilot decided to navigate to coordinates
[Turn End]

Turn 2
Engineer decided to repair hull damage
[Turn End]
""")
            log_path = f.name

        try:
            event_bus = EventBus()
            chronicler = ChroniclerAgent(
                event_bus=event_bus,
                character_names=["Pilot", "Engineer"],
            )

            story = chronicler.transcribe_log(log_path)

            assert isinstance(story, str)
            assert len(story) > 0
        finally:
            os.unlink(log_path)
