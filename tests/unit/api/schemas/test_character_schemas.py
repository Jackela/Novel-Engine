"""
Unit tests for Character API Schemas

Tests cover:
- CharacterPsychologySchema - Big Five personality model
- DialogueGenerationRequest/Response - Dialogue generation
- CharacterMemorySchema - Memory management
- CharacterGoalSchema - Goal management
- CharacterSummary/List/Detail - Character responses
- CharacterGenerationRequest/Response - Character generation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


class TestCharacterPsychologySchema:
    """Tests for CharacterPsychologySchema - Big Five personality model."""

    def test_valid_psychology_schema(self) -> None:
        """Test valid Big Five personality schema."""
        from src.api.schemas.character_schemas import CharacterPsychologySchema

        schema = CharacterPsychologySchema(
            openness=75,
            conscientiousness=60,
            extraversion=80,
            agreeableness=70,
            neuroticism=30,
        )

        assert schema.openness == 75
        assert schema.conscientiousness == 60
        assert schema.extraversion == 80
        assert schema.agreeableness == 70
        assert schema.neuroticism == 30

    def test_psychology_schema_boundary_values(self) -> None:
        """Test boundary values (0 and 100)."""
        from src.api.schemas.character_schemas import CharacterPsychologySchema

        schema = CharacterPsychologySchema(
            openness=0,
            conscientiousness=100,
            extraversion=50,
            agreeableness=50,
            neuroticism=50,
        )

        assert schema.openness == 0
        assert schema.conscientiousness == 100

    def test_psychology_schema_too_low(self) -> None:
        """Test validation for values below 0."""
        from src.api.schemas.character_schemas import CharacterPsychologySchema

        with pytest.raises(ValidationError) as exc_info:
            CharacterPsychologySchema(
                openness=-1,
                conscientiousness=50,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_psychology_schema_too_high(self) -> None:
        """Test validation for values above 100."""
        from src.api.schemas.character_schemas import CharacterPsychologySchema

        with pytest.raises(ValidationError) as exc_info:
            CharacterPsychologySchema(
                openness=50,
                conscientiousness=101,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )
        assert "100" in str(exc_info.value)

    def test_psychology_schema_required_fields(self) -> None:
        """Test that all Big Five fields are required."""
        from src.api.schemas.character_schemas import CharacterPsychologySchema

        with pytest.raises(ValidationError) as exc_info:
            CharacterPsychologySchema()
        assert "openness" in str(exc_info.value)


class TestDialogueGenerationRequest:
    """Tests for DialogueGenerationRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid dialogue generation request."""
        from src.api.schemas.character_schemas import DialogueGenerationRequest

        request = DialogueGenerationRequest(
            character_id="char_001",
            context="The hero confronts the villain in the throne room.",
            mood="angry",
        )

        assert request.character_id == "char_001"
        assert request.context == "The hero confronts the villain in the throne room."
        assert request.mood == "angry"
        assert request.psychology_override is None
        assert request.traits_override is None

    def test_request_with_overrides(self) -> None:
        """Test request with psychology and traits overrides."""
        from src.api.schemas.character_schemas import (
            DialogueGenerationRequest,
            CharacterPsychologySchema,
        )

        request = DialogueGenerationRequest(
            character_id="char_001",
            context="Test context",
            mood="excited",
            psychology_override=CharacterPsychologySchema(
                openness=80,
                conscientiousness=70,
                extraversion=90,
                agreeableness=60,
                neuroticism=40,
            ),
            traits_override=["brave", "honest"],
            speaking_style_override="Formal and eloquent",
        )

        assert request.psychology_override is not None
        assert request.psychology_override.openness == 80
        assert request.traits_override == ["brave", "honest"]
        assert request.speaking_style_override == "Formal and eloquent"

    def test_request_missing_required(self) -> None:
        """Test validation for missing required fields."""
        from src.api.schemas.character_schemas import DialogueGenerationRequest

        with pytest.raises(ValidationError) as exc_info:
            DialogueGenerationRequest(context="Test")
        assert "character_id" in str(exc_info.value)

    def test_request_context_too_long(self) -> None:
        """Test validation for context exceeding max length."""
        from src.api.schemas.character_schemas import DialogueGenerationRequest

        with pytest.raises(ValidationError) as exc_info:
            DialogueGenerationRequest(
                character_id="char_001",
                context="x" * 1001,  # Exceeds max_length of 1000
            )
        assert "at most 1000" in str(exc_info.value)

    def test_request_mood_too_long(self) -> None:
        """Test validation for mood exceeding max length."""
        from src.api.schemas.character_schemas import DialogueGenerationRequest

        with pytest.raises(ValidationError) as exc_info:
            DialogueGenerationRequest(
                character_id="char_001",
                context="Test",
                mood="x" * 51,  # Exceeds max_length of 50
            )
        assert "at most 50" in str(exc_info.value)

    def test_request_empty_context(self) -> None:
        """Test validation for empty context."""
        from src.api.schemas.character_schemas import DialogueGenerationRequest

        with pytest.raises(ValidationError) as exc_info:
            DialogueGenerationRequest(
                character_id="char_001",
                context="",
            )
        assert "String should have at least 1 character" in str(exc_info.value)


class TestDialogueGenerationResponse:
    """Tests for DialogueGenerationResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid dialogue generation response."""
        from src.api.schemas.character_schemas import DialogueGenerationResponse

        response = DialogueGenerationResponse(
            dialogue="I will not let you pass!",
            tone="defiant",
            internal_thought="This is my moment to stand firm.",
            body_language="stands with crossed arms",
            character_id="char_001",
        )

        assert response.dialogue == "I will not let you pass!"
        assert response.tone == "defiant"
        assert response.internal_thought == "This is my moment to stand firm."
        assert response.body_language == "stands with crossed arms"
        assert response.character_id == "char_001"
        assert response.error is None

    def test_response_with_error(self) -> None:
        """Test response with error message."""
        from src.api.schemas.character_schemas import DialogueGenerationResponse

        response = DialogueGenerationResponse(
            dialogue="",
            tone="neutral",
            character_id="char_001",
            error="Failed to generate dialogue",
        )

        assert response.error == "Failed to generate dialogue"


class TestCharacterMemorySchema:
    """Tests for CharacterMemorySchema."""

    def test_valid_memory(self) -> None:
        """Test valid memory schema."""
        from src.api.schemas.character_schemas import CharacterMemorySchema

        memory = CharacterMemorySchema(
            memory_id="mem_001",
            content="Defeated the dragon in the mountain cave.",
            importance=9,
            tags=["combat", "dragon", "victory"],
            timestamp="2024-01-15T10:30:00Z",
            is_core_memory=True,
            importance_level="core",
        )

        assert memory.memory_id == "mem_001"
        assert memory.importance == 9
        assert memory.is_core_memory is True

    def test_memory_importance_range(self) -> None:
        """Test importance validation (1-10)."""
        from src.api.schemas.character_schemas import CharacterMemorySchema

        # Too low
        with pytest.raises(ValidationError) as exc_info:
            CharacterMemorySchema(
                memory_id="mem_001",
                content="Test",
                importance=0,
                timestamp="2024-01-15T10:30:00Z",
            )
        assert "greater than or equal to 1" in str(exc_info.value)

        # Too high
        with pytest.raises(ValidationError) as exc_info:
            CharacterMemorySchema(
                memory_id="mem_001",
                content="Test",
                importance=11,
                timestamp="2024-01-15T10:30:00Z",
            )
        assert "less than or equal to 10" in str(exc_info.value)


class TestCharacterGoalSchema:
    """Tests for CharacterGoalSchema."""

    def test_valid_goal(self) -> None:
        """Test valid goal schema."""
        from src.api.schemas.character_schemas import CharacterGoalSchema

        goal = CharacterGoalSchema(
            goal_id="goal_001",
            description="Find the ancient artifact",
            status="ACTIVE",
            urgency="HIGH",
            created_at="2024-01-15T10:30:00Z",
            is_active=True,
            is_urgent=True,
        )

        assert goal.goal_id == "goal_001"
        assert goal.status == "ACTIVE"
        assert goal.urgency == "HIGH"
        assert goal.is_active is True

    def test_goal_status_validation(self) -> None:
        """Test status validation."""
        from src.api.schemas.character_schemas import CharacterGoalSchema

        # Valid statuses
        for status in ["ACTIVE", "COMPLETED", "FAILED", "active", "completed"]:
            goal = CharacterGoalSchema(
                goal_id="goal_001",
                description="Test",
                status=status,
                urgency="MEDIUM",
                created_at="2024-01-15T10:30:00Z",
            )
            assert goal.status == status.upper()

        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            CharacterGoalSchema(
                goal_id="goal_001",
                description="Test",
                status="INVALID",
                urgency="MEDIUM",
                created_at="2024-01-15T10:30:00Z",
            )
        assert "Status must be one of" in str(exc_info.value)

    def test_goal_urgency_validation(self) -> None:
        """Test urgency validation."""
        from src.api.schemas.character_schemas import CharacterGoalSchema

        # Valid urgencies
        for urgency in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            goal = CharacterGoalSchema(
                goal_id="goal_001",
                description="Test",
                status="ACTIVE",
                urgency=urgency,
                created_at="2024-01-15T10:30:00Z",
            )
            assert goal.urgency == urgency

        # Invalid urgency
        with pytest.raises(ValidationError) as exc_info:
            CharacterGoalSchema(
                goal_id="goal_001",
                description="Test",
                status="ACTIVE",
                urgency="INVALID",
                created_at="2024-01-15T10:30:00Z",
            )
        assert "Urgency must be one of" in str(exc_info.value)


class TestCharacterSummary:
    """Tests for CharacterSummary schema."""

    def test_valid_summary(self) -> None:
        """Test valid character summary."""
        from src.api.schemas.character_schemas import CharacterSummary

        summary = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Hero",
            status="active",
            type="character",
            updated_at="2024-01-15T10:30:00Z",
        )

        assert summary.id == "char_001"
        assert summary.name == "Hero"

    def test_summary_with_extended_fields(self) -> None:
        """Test summary with WORLD-001 enhanced fields."""
        from src.api.schemas.character_schemas import CharacterSummary

        summary = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Hero",
            status="active",
            type="character",
            updated_at="2024-01-15T10:30:00Z",
            aliases=["The Brave", "Dragonslayer"],
            archetype="Hero",
            traits=["brave", "honest", "strong"],
            appearance="Tall with armor",
            current_location_id="loc_001",
            is_deceased=False,
        )

        assert summary.aliases == ["The Brave", "Dragonslayer"]
        assert summary.archetype == "Hero"
        assert summary.current_location_id == "loc_001"
        assert summary.is_deceased is False

    def test_summary_defaults(self) -> None:
        """Test default values for optional fields."""
        from src.api.schemas.character_schemas import CharacterSummary

        summary = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Hero",
            status="active",
            type="character",
            updated_at="2024-01-15T10:30:00Z",
        )

        assert summary.aliases == []
        assert summary.traits == []
        assert summary.is_deceased is False
        assert summary.current_location_id is None


class TestCharacterDetailResponse:
    """Tests for CharacterDetailResponse schema."""

    def test_valid_detail(self) -> None:
        """Test valid character detail response."""
        from src.api.schemas.character_schemas import CharacterDetailResponse

        detail = CharacterDetailResponse(
            agent_id="char_001",
            character_id="char_001",
            character_name="Hero",
            name="The Hero",
            background_summary="A brave warrior from the north.",
            personality_traits="Brave, honorable, determined",
            current_status="active",
            narrative_context="Currently on a quest",
            skills={"strength": 85, "agility": 70},
            relationships={"ally": 90, "mentor": 80},
            current_location="Northern Kingdom",
            inventory=["sword", "shield", "potion"],
            metadata={"level": 10, "experience": 5000},
        )

        assert detail.agent_id == "char_001"
        assert detail.skills == {"strength": 85, "agility": 70}
        assert detail.inventory == ["sword", "shield", "potion"]

    def test_detail_defaults(self) -> None:
        """Test default values for optional fields."""
        from src.api.schemas.character_schemas import CharacterDetailResponse

        detail = CharacterDetailResponse(
            agent_id="char_001",
            character_id="char_001",
            character_name="Hero",
            name="Hero",
            background_summary="",
            personality_traits="",
            current_status="",
            narrative_context="",
        )

        assert detail.skills == {}
        assert detail.relationships == {}
        assert detail.inventory == []
        assert detail.metadata == {}
        assert detail.structured_data == {}


class TestCharacterGenerationRequest:
    """Tests for CharacterGenerationRequest schema."""

    def test_valid_request(self) -> None:
        """Test valid character generation request."""
        from src.api.schemas.character_schemas import CharacterGenerationRequest

        request = CharacterGenerationRequest(
            concept="A brave knight who protects the realm",
            archetype="Paladin",
            tone="heroic",
        )

        assert request.concept == "A brave knight who protects the realm"
        assert request.archetype == "Paladin"
        assert request.tone == "heroic"

    def test_request_optional_tone(self) -> None:
        """Test request with optional tone."""
        from src.api.schemas.character_schemas import CharacterGenerationRequest

        request = CharacterGenerationRequest(
            concept="A mysterious wizard",
            archetype="Mage",
        )

        assert request.tone is None


class TestCharacterGenerationResponse:
    """Tests for CharacterGenerationResponse schema."""

    def test_valid_response(self) -> None:
        """Test valid character generation response."""
        from src.api.schemas.character_schemas import CharacterGenerationResponse

        response = CharacterGenerationResponse(
            name="Sir Valor",
            tagline="The Shield of the Realm",
            bio="A noble knight sworn to protect the innocent.",
            visual_prompt="Tall knight in shining armor with a blue cape",
            traits=["brave", "honorable", "stoic", "protective"],
        )

        assert response.name == "Sir Valor"
        assert response.tagline == "The Shield of the Realm"
        assert len(response.traits) == 4


class TestCharacterProfileGeneration:
    """Tests for character profile generation schemas."""

    def test_profile_generation_request(self) -> None:
        """Test profile generation request."""
        from src.api.schemas.character_schemas import CharacterProfileGenerationRequest

        request = CharacterProfileGenerationRequest(
            name="Elena",
            archetype="Rogue",
            context="A thief in a steampunk city",
        )

        assert request.name == "Elena"
        assert request.archetype == "Rogue"
        assert request.context == "A thief in a steampunk city"

    def test_profile_generation_request_name_validation(self) -> None:
        """Test name length validation."""
        from src.api.schemas.character_schemas import CharacterProfileGenerationRequest

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            CharacterProfileGenerationRequest(
                name="x" * 101,
                archetype="Warrior",
            )
        assert "100" in str(exc_info.value)

        # Empty
        with pytest.raises(ValidationError) as exc_info:
            CharacterProfileGenerationRequest(
                name="",
                archetype="Warrior",
            )
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_profile_generation_response(self) -> None:
        """Test profile generation response."""
        from src.api.schemas.character_schemas import CharacterProfileGenerationResponse

        response = CharacterProfileGenerationResponse(
            name="Elena",
            aliases=["The Shadow", "Ghost"],
            archetype="Rogue",
            traits=["stealthy", "clever", "cautious"],
            appearance="Slim build, dark clothing, piercing eyes",
            backstory="Raised on the streets, learned to survive",
            motivations=["Find her lost brother", "Escape poverty"],
            quirks=["Always checks exits", "Hoards small items"],
        )

        assert response.name == "Elena"
        assert response.aliases == ["The Shadow", "Ghost"]
        assert len(response.motivations) == 2
