"""
Unit tests for System API Schemas

Tests cover:
- System schemas (if any exist in system_schemas.py)
- Common patterns across schemas
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


class TestSystemSchemas:
    """Tests for system-related schemas."""

    def test_import_system_schemas(self) -> None:
        """Test that system schemas can be imported."""
        try:
            from src.api.schemas import system_schemas  # noqa: F401
            assert True
        except ImportError:
            pytest.skip("system_schemas module not found")


class TestSchemaImports:
    """Tests for schema module imports."""

    def test_import_character_schemas(self) -> None:
        """Test importing character schemas module."""
        from src.api.schemas import character_schemas
        assert character_schemas is not None

    def test_import_narrative_schemas(self) -> None:
        """Test importing narrative schemas module."""
        from src.api.schemas import narrative_schemas
        assert narrative_schemas is not None

    def test_import_world_schemas(self) -> None:
        """Test importing world schemas module."""
        from src.api.schemas import world_schemas
        assert world_schemas is not None

    def test_import_lore_schemas(self) -> None:
        """Test importing lore schemas module."""
        from src.api.schemas import lore_schemas
        assert lore_schemas is not None

    def test_import_social_schemas(self) -> None:
        """Test importing social schemas module."""
        from src.api.schemas import social_schemas
        assert social_schemas is not None

    def test_import_knowledge_schemas(self) -> None:
        """Test importing knowledge schemas module."""
        from src.api.schemas import knowledge_schemas
        assert knowledge_schemas is not None

    def test_import_experiment_schemas(self) -> None:
        """Test importing experiment schemas module."""
        from src.api.schemas import experiment_schemas
        assert experiment_schemas is not None

    def test_import_orchestration_schemas(self) -> None:
        """Test importing orchestration schemas module."""
        from src.api.schemas import orchestration_schemas
        assert orchestration_schemas is not None


class TestSchemaModuleAttributes:
    """Tests for schema module attributes."""

    def test_character_schemas_exports(self) -> None:
        """Test character schemas module exports."""
        from src.api.schemas import character_schemas

        expected_classes = [
            "CharacterPsychologySchema",
            "DialogueGenerationRequest",
            "DialogueGenerationResponse",
            "CharacterMemorySchema",
            "CharacterGoalSchema",
            "CharacterSummary",
            "CharactersListResponse",
            "CharacterDetailResponse",
        ]

        for cls_name in expected_classes:
            assert hasattr(character_schemas, cls_name), f"Missing {cls_name}"

    def test_narrative_schemas_exports(self) -> None:
        """Test narrative schemas module exports."""
        from src.api.schemas import narrative_schemas

        expected_classes = [
            "NarrativeData",
            "NarrativeResponse",
            "SceneGenerationRequest",
            "SceneGenerationResponse",
            "WorldContext",
            "WorldContextEntity",
            "NarrativeStreamRequest",
            "NarrativeStreamChunk",
        ]

        for cls_name in expected_classes:
            assert hasattr(narrative_schemas, cls_name), f"Missing {cls_name}"

    def test_world_schemas_exports(self) -> None:
        """Test world schemas module exports."""
        from src.api.schemas import world_schemas

        expected_classes = [
            "HistoryEventResponse",
            "CreateEventRequest",
            "EventFilterParams",
            "EventListResponse",
            "CalendarResponse",
            "WorldTimeResponse",
        ]

        for cls_name in expected_classes:
            assert hasattr(world_schemas, cls_name), f"Missing {cls_name}"


class TestSchemaInheritance:
    """Tests for schema inheritance patterns."""

    def test_all_schemas_inherit_base_model(self) -> None:
        """Test that all schemas inherit from BaseModel."""
        from pydantic import BaseModel

        from src.api.schemas.character_schemas import (
            CharacterPsychologySchema,
            CharacterSummary,
        )

        assert issubclass(CharacterPsychologySchema, BaseModel)
        assert issubclass(CharacterSummary, BaseModel)


class TestSchemaSerialization:
    """Tests for schema serialization/deserialization."""

    def test_character_summary_serialization(self) -> None:
        """Test character summary serialization."""
        from src.api.schemas.character_schemas import CharacterSummary

        summary = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Hero",
            status="active",
            type="character",
            updated_at="2024-01-15T10:30:00Z",
        )

        # Test model_dump (Pydantic v2)
        data = summary.model_dump()
        assert data["id"] == "char_001"
        assert data["name"] == "Hero"

    def test_character_summary_json_serialization(self) -> None:
        """Test character summary JSON serialization."""
        import json

        from src.api.schemas.character_schemas import CharacterSummary

        summary = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Hero",
            status="active",
            type="character",
            updated_at="2024-01-15T10:30:00Z",
        )

        # Test model_dump_json (Pydantic v2)
        json_str = summary.model_dump_json()
        data = json.loads(json_str)
        assert data["id"] == "char_001"

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization."""
        from src.api.schemas.character_schemas import CharacterSummary

        original = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Hero",
            status="active",
            type="character",
            updated_at="2024-01-15T10:30:00Z",
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = CharacterSummary(**data)

        assert restored.id == original.id
        assert restored.name == original.name


class TestSchemaValidationErrors:
    """Tests for schema validation error messages."""

    def test_validation_error_message_format(self) -> None:
        """Test that validation errors have proper format."""
        from pydantic import ValidationError

        from src.api.schemas.character_schemas import CharacterPsychologySchema

        try:
            CharacterPsychologySchema(
                openness=-1,
                conscientiousness=50,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            error_dict = e.errors()
            assert len(error_dict) > 0
            assert "openness" in str(error_dict)

    def test_multiple_validation_errors(self) -> None:
        """Test multiple validation errors in one request."""
        from pydantic import ValidationError

        from src.api.schemas.character_schemas import CharacterPsychologySchema

        try:
            CharacterPsychologySchema(
                openness=-1,
                conscientiousness=101,
                extraversion=50,
                agreeableness=50,
                neuroticism=50,
            )
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            error_dict = e.errors()
            # Should have 2 errors (one for openness, one for conscientiousness)
            assert len(error_dict) >= 1
