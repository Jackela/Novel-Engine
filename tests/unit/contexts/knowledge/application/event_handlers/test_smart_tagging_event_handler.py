"""
Tests for SmartTaggingEventHandler

Unit tests for the event handler that automatically generates tags
for content when entities are created or updated.

Warzone 4: AI Brain - BRAIN-038-03
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from src.contexts.knowledge.application.event_handlers.smart_tagging_event_handler import (
    SmartTaggingEventHandler,
)
from src.contexts.knowledge.application.services.smart_tagging_service import (
    GeneratedTag,
    TagCategory,
    TaggingConfig,
    TaggingResult,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
class TestSmartTaggingEventHandler:
    """Tests for SmartTaggingEventHandler."""

    @pytest.fixture
    def mock_tagging_service(self) -> Mock:
        """Create a mock smart tagging service."""
        service = Mock()

        # Mock response for lore content
        service.generate_tags = AsyncMock(
            return_value=TaggingResult(
                content_type="lore",
                tags=[
                    GeneratedTag(category=TagCategory.GENRE, value="fantasy"),
                    GeneratedTag(category=TagCategory.MOOD, value="mysterious"),
                    GeneratedTag(category=TagCategory.THEMES, value="good-vs-evil"),
                    GeneratedTag(
                        category=TagCategory.CHARACTERS_PRESENT, value="gandalf"
                    ),
                    GeneratedTag(category=TagCategory.LOCATIONS, value="shire"),
                ],
            )
        )
        return service

    @pytest.fixture
    def handler(self, mock_tagging_service: Mock) -> SmartTaggingEventHandler:
        """Create a handler instance for testing."""
        return SmartTaggingEventHandler(
            tagging_service=mock_tagging_service,
            enabled=True,
        )

    @pytest.mark.asyncio
    async def test_handler_initialization(
        self, handler: SmartTaggingEventHandler
    ) -> None:
        """Test handler initializes correctly."""
        assert handler.is_enabled() is True
        assert handler._tagging_service is not None

    @pytest.mark.asyncio
    async def test_handler_disabled(self, mock_tagging_service: Mock) -> None:
        """Test handler when disabled returns existing tags."""
        handler = SmartTaggingEventHandler(
            tagging_service=mock_tagging_service,
            enabled=False,
        )

        assert handler.is_enabled() is False

        # Should return empty dict when disabled and no existing tags
        result = await handler.generate_tags_for_lore(
            lore_id="lore-001",
            title="Test Lore",
            content="Test content",
        )

        assert result == {}

        # Should return existing tags when provided
        existing = {"genre": ["fantasy"], "mood": ["dark"]}
        result = await handler.generate_tags_for_lore(
            lore_id="lore-001",
            title="Test Lore",
            content="Test content",
            existing_tags=existing,
        )

        assert result == existing

        # Service should not have been called
        mock_tagging_service.generate_tags.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_tags_for_lore(
        self,
        handler: SmartTaggingEventHandler,
        mock_tagging_service: Mock,
    ) -> None:
        """Test generating tags for lore entry."""
        result = await handler.generate_tags_for_lore(
            lore_id="lore-001",
            title="The Ancient Sword",
            content="A legendary weapon forged in the fires of Mount Doom",
            category="artifact",
        )

        # Verify tags were returned
        assert "genre" in result
        assert "fantasy" in result["genre"]
        assert "mood" in result
        assert "mysterious" in result["mood"]
        assert "themes" in result
        assert "good-vs-evil" in result["themes"]
        assert "characters_present" in result
        assert "gandalf" in result["characters_present"]
        assert "locations" in result
        assert "shire" in result["locations"]

        # Verify service was called
        mock_tagging_service.generate_tags.assert_called_once()
        # Check that content_type was lore
        # The actual content is built by _build_lore_content and contains the title
        assert handler._build_lore_content(
            "The Ancient Sword",
            "A legendary weapon forged in the fires of Mount Doom",
            "artifact",
        ) == (
            "# The Ancient Sword\nCategory: artifact\n\nA legendary weapon forged in the fires of Mount Doom"
        )

    @pytest.mark.asyncio
    async def test_generate_tags_for_lore_preserves_existing_tags(
        self,
        handler: SmartTaggingEventHandler,
        mock_tagging_service: Mock,
    ) -> None:
        """Test that existing tags are preserved when merging."""
        existing_tags = {
            "genre": ["fantasy", "horror"],  # horror should be preserved
            "mood": ["dark"],  # should be merged with mysterious
            "custom_category": ["custom_tag"],  # custom category preserved
        }

        result = await handler.generate_tags_for_lore(
            lore_id="lore-001",
            title="The Ancient Sword",
            content="Content",
            existing_tags=existing_tags,
        )

        # Both fantasy and horror should be present
        assert "fantasy" in result["genre"]
        assert "horror" in result["genre"]

        # Both dark and mysterious should be present
        assert "dark" in result["mood"]
        assert "mysterious" in result["mood"]

        # Custom category should be preserved
        assert "custom_category" in result
        assert "custom_tag" in result["custom_category"]

    @pytest.mark.asyncio
    async def test_generate_tags_for_scene(
        self,
        handler: SmartTaggingEventHandler,
        mock_tagging_service: Mock,
    ) -> None:
        """Test generating tags for scene."""
        result = await handler.generate_tags_for_scene(
            scene_id="scene-001",
            title="The Battle",
            summary="Epic battle scene",
            location="Minas Tirith",
            beats=["The armies clash", "Heroes fall"],
        )

        # Verify tags structure
        assert "genre" in result
        assert "mood" in result

        # Verify service was called with scene content type
        mock_tagging_service.generate_tags.assert_called_once()
        call_args = mock_tagging_service.generate_tags.call_args
        assert call_args[1]["content_type"] == "scene"

    @pytest.mark.asyncio
    async def test_generate_tags_for_character(
        self,
        handler: SmartTaggingEventHandler,
        mock_tagging_service: Mock,
    ) -> None:
        """Test generating tags for character."""
        result = await handler.generate_tags_for_character(
            character_id="char-001",
            name="Aragorn",
            description="Ranger of the North",
            backstory="Heir to the throne",
            traits=["brave", "noble"],
        )

        # Verify tags structure
        assert "genre" in result

        # Verify service was called with character content type
        mock_tagging_service.generate_tags.assert_called_once()
        call_args = mock_tagging_service.generate_tags.call_args
        assert call_args[1]["content_type"] == "character"

    @pytest.mark.asyncio
    async def test_generate_tags_handles_error_gracefully(
        self,
        mock_tagging_service: Mock,
    ) -> None:
        """Test that tagging errors are handled gracefully."""
        # Make the service raise an error
        mock_tagging_service.generate_tags.side_effect = Exception("LLM error")

        handler = SmartTaggingEventHandler(
            tagging_service=mock_tagging_service,
            enabled=True,
        )

        # Should return empty dict on error
        result = await handler.generate_tags_for_lore(
            lore_id="lore-001",
            title="Test",
            content="Content",
        )

        assert result == {}

    @pytest.mark.asyncio
    async def test_set_enabled(self, handler: SmartTaggingEventHandler) -> None:
        """Test enabling/disabling the handler."""
        assert handler.is_enabled() is True

        handler.set_enabled(False)
        assert handler.is_enabled() is False

        handler.set_enabled(True)
        assert handler.is_enabled() is True

    def test_build_lore_content(self, handler: SmartTaggingEventHandler) -> None:
        """Test building content string for lore."""
        content = handler._build_lore_content(
            title="The Sword",
            content="A sharp blade",
            category="weapon",
        )

        assert "# The Sword" in content
        assert "Category: weapon" in content
        assert "A sharp blade" in content

    def test_build_scene_content(self, handler: SmartTaggingEventHandler) -> None:
        """Test building content string for scene."""
        content = handler._build_scene_content(
            title="The Battle",
            summary="Epic fight",
            location="Minas Tirith",
            beats=["Charge!", "Retreat!"],
        )

        assert "# The Battle" in content
        assert "Location: Minas Tirith" in content
        assert "Summary: Epic fight" in content
        assert "Charge!" in content
        assert "Retreat!" in content

    def test_build_character_content(self, handler: SmartTaggingEventHandler) -> None:
        """Test building content string for character."""
        content = handler._build_character_content(
            name="Aragorn",
            description="Ranger",
            backstory="Heir to throne",
            traits=["brave", "noble"],
        )

        assert "# Aragorn" in content
        assert "Traits: brave, noble" in content
        assert "Description: Ranger" in content
        assert "Backstory: Heir to throne" in content

    def test_result_to_dict(self, handler: SmartTaggingEventHandler) -> None:
        """Test converting TaggingResult to dictionary."""
        result = TaggingResult(
            content_type="lore",
            tags=[
                GeneratedTag(category=TagCategory.GENRE, value="fantasy"),
                GeneratedTag(category=TagCategory.GENRE, value="adventure"),
                GeneratedTag(category=TagCategory.MOOD, value="dark"),
            ],
        )

        tags_dict = handler._result_to_dict(result)

        assert tags_dict["genre"] == ["fantasy", "adventure"]
        assert tags_dict["mood"] == ["dark"]

    def test_merge_tags(self, handler: SmartTaggingEventHandler) -> None:
        """Test merging generated tags with existing tags."""
        generated = {
            "genre": ["fantasy"],
            "mood": ["mysterious"],
        }

        existing = {
            "genre": ["horror"],  # Should be merged
            "mood": ["dark"],  # Should be merged
            "custom": ["tag"],  # Should be preserved
        }

        merged = handler._merge_tags(generated, existing)

        # All genres should be present
        assert set(merged["genre"]) == {"fantasy", "horror"}

        # All moods should be present
        assert set(merged["mood"]) == {"mysterious", "dark"}

        # Custom category should be preserved
        assert merged["custom"] == ["tag"]

    def test_merge_tags_removes_duplicates(
        self, handler: SmartTaggingEventHandler
    ) -> None:
        """Test that merging removes duplicate tags."""
        generated = {
            "genre": ["fantasy", "adventure"],
        }

        existing = {
            "genre": ["fantasy", "horror"],  # fantasy is duplicate
        }

        merged = handler._merge_tags(generated, existing)

        # Should have unique tags only
        assert set(merged["genre"]) == {"fantasy", "adventure", "horror"}
        assert len(merged["genre"]) == 3


@pytest.mark.unit
class TestSmartTaggingEventHandlerIntegration:
    """Integration tests for SmartTaggingEventHandler."""

    @pytest.mark.asyncio
    async def test_end_to_end_lore_tagging(self) -> None:
        """Test complete flow of tagging a lore entry."""
        # Create a mock LLM client
        mock_llm = Mock()
        mock_llm.generate = AsyncMock(
            return_value=Mock(
                text='{"genre": ["fantasy"], "mood": ["mysterious"], '
                '"themes": ["quest"], "characters_present": [], "locations": []}'
            )
        )

        # Import and create actual SmartTaggingService
        from src.contexts.knowledge.application.services.smart_tagging_service import (
            SmartTaggingService,
        )

        tagging_service = SmartTaggingService(llm_client=mock_llm)
        handler = SmartTaggingEventHandler(
            tagging_service=tagging_service, enabled=True
        )

        # Generate tags
        result = await handler.generate_tags_for_lore(
            lore_id="lore-001",
            title="The One Ring",
            content="A powerful ring that must be destroyed",
            category="artifact",
        )

        # Verify result
        assert "genre" in result
        assert "fantasy" in result["genre"]
        assert "mood" in result
        assert "mysterious" in result["mood"]
        assert "themes" in result
        assert "quest" in result["themes"]

        # Verify LLM was called
        mock_llm.generate.assert_called_once()
