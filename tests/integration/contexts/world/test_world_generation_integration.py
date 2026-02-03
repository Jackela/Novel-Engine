"""Integration tests for world generation.

These tests verify that LLM-generated world data can be successfully
parsed into valid domain entities.
"""

import json
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.contexts.world.application.ports.world_generator_port import (
    WorldGenerationInput,
)
from src.contexts.world.domain.entities import (
    Era,
    EventSignificance,
    FactionType,
    Genre,
    LocationType,
    ToneType,
)
from src.contexts.world.infrastructure.generators.llm_world_generator import (
    LLMWorldGenerator,
)


def create_realistic_llm_response() -> Dict[str, Any]:
    """Create a realistic LLM response that mimics actual Gemini output."""
    return {
        "world_setting": {
            "name": "The Shattered Realms",
            "description": "A once-unified empire now fractured into warring kingdoms, where ancient magic resurfaces through crystalline ley lines.",
            "themes": ["political intrigue", "redemption", "the cost of power"],
            "world_rules": [
                "Magic flows through ley lines visible as faint crystalline veins",
                "Only those born during celestial events can channel raw magic",
                "The old gods slumber but can be awakened"
            ],
            "cultural_influences": ["Medieval Europe", "Byzantine Empire", "Celtic mythology"]
        },
        "locations": [
            {
                "temp_id": "temp_location_1",
                "name": "Valdris, the Cracked Crown",
                "description": "The former imperial capital, now split by a massive ley line that tore through during the Sundering.",
                "location_type": "capital",
                "climate": "temperate",
                "status": "contested",
                "population": 85000,
                "notable_features": ["The Split Palace", "Ley Line Chasm", "Bridge of Chains"],
                "resources": ["magical crystals", "iron", "scholars"],
                "dangers": ["unstable magic zones", "political assassination"],
                "accessibility": 70,
                "wealth_level": 65,
                "magic_concentration": 95,
                "parent_location_id": None,
                "child_location_ids": ["temp_location_2"],
                "connections": ["temp_location_3", "temp_location_4"]
            },
            {
                "temp_id": "temp_location_2",
                "name": "The Undercity",
                "description": "Tunnels beneath Valdris where the desperate and criminal make their home.",
                "location_type": "dungeon",
                "climate": "artificial",
                "status": "thriving",
                "population": 12000,
                "notable_features": ["Thieves Guild Hall", "Smuggler's Market"],
                "resources": ["information", "contraband"],
                "dangers": ["gang violence", "unstable tunnels"],
                "accessibility": 30,
                "wealth_level": 40,
                "magic_concentration": 20,
                "parent_location_id": "temp_location_1",
                "child_location_ids": [],
                "connections": []
            },
            {
                "temp_id": "temp_location_3",
                "name": "The Ironwood",
                "description": "A vast forest where trees have turned metallic, corrupted by wild magic.",
                "location_type": "forest",
                "climate": "temperate",
                "status": "stable",
                "population": 500,
                "notable_features": ["Iron Oak Grove", "Hermit's Sanctum"],
                "resources": ["ironwood timber", "rare herbs"],
                "dangers": ["corrupted beasts", "magic storms"],
                "accessibility": 35,
                "wealth_level": 25,
                "magic_concentration": 75,
                "parent_location_id": None,
                "child_location_ids": [],
                "connections": ["temp_location_1"]
            },
            {
                "temp_id": "temp_location_4",
                "name": "Port Meridian",
                "description": "The largest trading hub, controlled by the Merchant Princes.",
                "location_type": "port",
                "climate": "mediterranean",
                "status": "thriving",
                "population": 120000,
                "notable_features": ["The Grand Exchange", "Lighthouse of Ages"],
                "resources": ["foreign goods", "ships", "gold"],
                "dangers": ["pirates", "smugglers"],
                "accessibility": 90,
                "wealth_level": 85,
                "magic_concentration": 30,
                "parent_location_id": None,
                "child_location_ids": [],
                "connections": ["temp_location_1"]
            },
            {
                "temp_id": "temp_location_5",
                "name": "The Sunken Temple",
                "description": "An ancient temple to the old gods, half submerged in a sacred lake.",
                "location_type": "temple",
                "climate": "temperate",
                "status": "abandoned",
                "population": 0,
                "notable_features": ["Submerged altar", "Prophetic murals"],
                "resources": ["ancient artifacts"],
                "dangers": ["guardian spirits", "drowning hazards"],
                "accessibility": 15,
                "wealth_level": 60,
                "magic_concentration": 100,
                "parent_location_id": None,
                "child_location_ids": [],
                "connections": []
            }
        ],
        "factions": [
            {
                "temp_id": "temp_faction_1",
                "name": "The Remnant Throne",
                "description": "Loyalists who seek to restore the shattered empire under the rightful heir.",
                "faction_type": "kingdom",
                "alignment": "lawful_neutral",
                "status": "active",
                "leader_name": "Prince Aldric the Exile",
                "founding_date": "Year 1 After Sundering",
                "values": ["unity", "legitimacy", "tradition"],
                "goals": ["Reunify the realms", "Crown Prince Aldric", "Rebuild Valdris"],
                "resources": ["veteran soldiers", "noble supporters", "ancient claims"],
                "influence": 60,
                "military_strength": 70,
                "economic_power": 45,
                "member_count": 15000,
                "headquarters_id": "temp_location_1",
                "territories": ["temp_location_1"]
            },
            {
                "temp_id": "temp_faction_2",
                "name": "The Merchant Princes",
                "description": "A council of wealthy traders who profit from the chaos of division.",
                "faction_type": "merchant",
                "alignment": "true_neutral",
                "status": "active",
                "leader_name": "High Merchant Cassandra Vex",
                "founding_date": "Year 5 After Sundering",
                "values": ["profit", "neutrality", "opportunity"],
                "goals": ["Maintain division", "Control trade routes", "Acquire ley crystals"],
                "resources": ["vast wealth", "trade fleets", "mercenaries"],
                "influence": 75,
                "military_strength": 40,
                "economic_power": 95,
                "member_count": 500,
                "headquarters_id": "temp_location_4",
                "territories": ["temp_location_4"]
            },
            {
                "temp_id": "temp_faction_3",
                "name": "The Ley Wardens",
                "description": "Mages sworn to protect and study the ley lines.",
                "faction_type": "academic",
                "alignment": "neutral_good",
                "status": "active",
                "leader_name": "Archmagus Serina",
                "founding_date": "Year 12 After Sundering",
                "values": ["knowledge", "balance", "protection"],
                "goals": ["Understand the Sundering", "Prevent magical catastrophe", "Train new mages"],
                "resources": ["magical knowledge", "ley line access", "ancient texts"],
                "influence": 50,
                "military_strength": 60,
                "economic_power": 30,
                "member_count": 200,
                "headquarters_id": "temp_location_3",
                "territories": ["temp_location_3", "temp_location_5"]
            }
        ],
        "events": [
            {
                "temp_id": "temp_event_1",
                "name": "The Sundering",
                "description": "A magical catastrophe that shattered the empire when Emperor Valen attempted to bind all ley lines to his will.",
                "event_type": "disaster",
                "significance": "world_changing",
                "outcome": "negative",
                "date_description": "Year 0, the last day of the Old Empire",
                "duration_description": "A single catastrophic hour",
                "location_ids": ["temp_location_1"],
                "faction_ids": [],
                "key_figures": ["Emperor Valen the Ambitious", "Archmage Thorn"],
                "causes": ["Imperial overreach", "Lust for absolute power"],
                "consequences": ["Empire shattered", "Ley lines exposed", "Millions dead"],
                "preceding_event_ids": [],
                "following_event_ids": ["temp_event_2", "temp_event_3"],
                "related_event_ids": [],
                "is_secret": False,
                "narrative_importance": 100
            },
            {
                "temp_id": "temp_event_2",
                "name": "The Prince's Flight",
                "description": "Young Prince Aldric escaped the destruction, spirited away by loyal guards.",
                "event_type": "migration",
                "significance": "major",
                "outcome": "mixed",
                "date_description": "Year 0, during the Sundering",
                "duration_description": "Three desperate days",
                "location_ids": ["temp_location_1", "temp_location_3"],
                "faction_ids": ["temp_faction_1"],
                "key_figures": ["Prince Aldric", "Captain Mira"],
                "causes": ["The Sundering", "Loyalty of the guard"],
                "consequences": ["Legitimate heir survived", "Remnant Throne founded"],
                "preceding_event_ids": ["temp_event_1"],
                "following_event_ids": [],
                "related_event_ids": [],
                "is_secret": False,
                "narrative_importance": 80
            },
            {
                "temp_id": "temp_event_3",
                "name": "Rise of the Merchant Princes",
                "description": "Wealthy traders filled the power vacuum, establishing Port Meridian as the new center of commerce.",
                "event_type": "economic",
                "significance": "major",
                "outcome": "positive",
                "date_description": "Years 1-5 After Sundering",
                "duration_description": "Five years of consolidation",
                "location_ids": ["temp_location_4"],
                "faction_ids": ["temp_faction_2"],
                "key_figures": ["Founder Marcus Vex", "The Original Five"],
                "causes": ["The Sundering", "Collapse of imperial trade"],
                "consequences": ["New economic power", "Trade routes restructured"],
                "preceding_event_ids": ["temp_event_1"],
                "following_event_ids": [],
                "related_event_ids": [],
                "is_secret": False,
                "narrative_importance": 70
            }
        ]
    }


@pytest.fixture
def generator() -> LLMWorldGenerator:
    """Create a generator instance for testing.

    Note: We set _api_key directly to avoid dependency on environment variables,
    which may not be set in CI environments. The actual API call is mocked anyway.
    """
    gen = LLMWorldGenerator()
    gen._api_key = "test-api-key"  # Set directly since env var might not exist in CI
    return gen


@pytest.fixture
def realistic_response() -> Dict[str, Any]:
    """Provide realistic LLM response."""
    return create_realistic_llm_response()


class TestWorldGenerationIntegration:
    """Integration tests for complete world generation flow."""

    @pytest.mark.integration
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_generate_fantasy_world_parses_to_valid_entities(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        realistic_response: Dict[str, Any],
    ) -> None:
        """Test that a generated fantasy world produces valid domain entities."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(realistic_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            request = WorldGenerationInput(
                genre=Genre.FANTASY,
                era=Era.MEDIEVAL,
                tone=ToneType.EPIC,
                themes=["political intrigue", "redemption"],
                magic_level=8,
                technology_level=3,
                num_factions=3,
                num_locations=5,
                num_events=3,
            )
            result = generator.generate(request)

        # Verify world setting
        assert result.world_setting.name == "The Shattered Realms"
        assert result.world_setting.genre == Genre.FANTASY
        assert result.world_setting.era == Era.MEDIEVAL
        assert len(result.world_setting.themes) > 0

        # Verify locations
        assert len(result.locations) == 5
        capital = next(
            (loc for loc in result.locations if loc.location_type == LocationType.CAPITAL),
            None,
        )
        assert capital is not None
        assert capital.name == "Valdris, the Cracked Crown"
        assert capital.population == 85000

        # Verify parent-child relationships resolved
        undercity = next(
            (loc for loc in result.locations if "Undercity" in loc.name), None
        )
        assert undercity is not None
        assert undercity.parent_location_id == capital.id

        # Verify factions
        assert len(result.factions) == 3
        kingdom = next(
            (f for f in result.factions if f.faction_type == FactionType.KINGDOM), None
        )
        assert kingdom is not None
        assert kingdom.name == "The Remnant Throne"
        assert kingdom.headquarters_id == capital.id  # Resolved reference

        # Verify events
        assert len(result.events) == 3
        sundering = next(
            (e for e in result.events if e.significance == EventSignificance.WORLD_CHANGING),
            None,
        )
        assert sundering is not None
        assert sundering.name == "The Sundering"
        assert sundering.narrative_importance == 100

        # Verify event causality chain
        flight = next(
            (e for e in result.events if "Flight" in e.name), None
        )
        assert flight is not None
        assert sundering.id in flight.preceding_event_ids
        assert flight.id in sundering.following_event_ids

    @pytest.mark.integration
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_generate_with_markdown_wrapped_json(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        realistic_response: Dict[str, Any],
    ) -> None:
        """Test generation when LLM wraps JSON in markdown code blocks."""
        # Wrap the JSON in markdown code blocks (common LLM behavior)
        wrapped_content = f"""Here is the generated world:

```json
{json.dumps(realistic_response, indent=2)}
```

I hope this world meets your needs!"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": wrapped_content}]}}]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            request = WorldGenerationInput()
            result = generator.generate(request)

        assert result.world_setting.name == "The Shattered Realms"
        assert len(result.factions) == 3

    @pytest.mark.integration
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_generate_handles_partial_data_gracefully(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
    ) -> None:
        """Test that generator handles incomplete LLM response gracefully."""
        partial_response = {
            "world_setting": {
                "name": "Minimal World",
                "description": "A simple test world",
            },
            "locations": [
                {
                    "temp_id": "temp_loc_1",
                    "name": "Test Location",
                    # Missing most fields - should use defaults
                }
            ],
            "factions": [],
            "events": [],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(partial_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            request = WorldGenerationInput()
            result = generator.generate(request)

        # Should still produce valid result with defaults
        assert result.world_setting.name == "Minimal World"
        assert len(result.locations) == 1
        assert result.locations[0].name == "Test Location"
        assert result.locations[0].location_type == LocationType.REGION  # Default

    @pytest.mark.integration
    @patch("src.contexts.world.infrastructure.generators.llm_world_generator.requests.post")
    def test_cross_references_resolve_correctly(
        self,
        mock_post: MagicMock,
        generator: LLMWorldGenerator,
        realistic_response: Dict[str, Any],
    ) -> None:
        """Test that all cross-references between entities resolve correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps(realistic_response)}]}}
            ]
        }
        mock_post.return_value = mock_response

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}):
            result = generator.generate(WorldGenerationInput())

        # Build ID sets for validation
        location_ids = {loc.id for loc in result.locations}
        faction_ids = {fac.id for fac in result.factions}
        event_ids = {evt.id for evt in result.events}

        # Verify location references
        for loc in result.locations:
            if loc.parent_location_id:
                assert loc.parent_location_id in location_ids
            for child_id in loc.child_location_ids:
                assert child_id in location_ids
            for conn_id in loc.connections:
                assert conn_id in location_ids

        # Verify faction references
        for fac in result.factions:
            if fac.headquarters_id:
                assert fac.headquarters_id in location_ids
            for terr_id in fac.territories:
                assert terr_id in location_ids

        # Verify event references
        for evt in result.events:
            for loc_id in evt.location_ids:
                assert loc_id in location_ids
            for fac_id in evt.faction_ids:
                assert fac_id in faction_ids
            for pre_id in evt.preceding_event_ids:
                assert pre_id in event_ids
            for fol_id in evt.following_event_ids:
                assert fol_id in event_ids
