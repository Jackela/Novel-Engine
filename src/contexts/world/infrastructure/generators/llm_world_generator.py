"""LLM-based world generator using Gemini API.

This module implements the WorldGeneratorPort protocol using Google's Gemini API
to generate complete world lore including settings, factions, locations, and
historical events in a single pass.

The generator uses structured prompts to produce JSON output that is then
parsed into domain entities. It handles temporary ID cross-references to
maintain entity relationships during generation.

Additionally, this module provides dialogue generation capabilities that create
character-authentic speech based on psychology, traits, and speaking style.

Typical usage example:
    >>> from src.contexts.world.infrastructure.generators import LLMWorldGenerator
    >>> from src.contexts.world.application.ports import WorldGenerationInput, Genre
    >>> generator = LLMWorldGenerator(temperature=0.8)
    >>> request = WorldGenerationInput(
    ...     genre=Genre.FANTASY,
    ...     num_factions=3,
    ...     num_locations=5
    ... )
    >>> result = generator.generate(request)
    >>> print(result.generation_summary)

    # Dialogue generation example:
    >>> dialogue_result = generator.generate_dialogue(
    ...     character=my_character,
    ...     context="A stranger approaches in the tavern",
    ...     mood="suspicious"
    ... )
    >>> print(dialogue_result.dialogue)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import requests
import structlog
import yaml

from src.contexts.world.application.ports.world_generator_port import (
    WorldGenerationInput,
    WorldGenerationResult,
    WorldGeneratorPort,
)
from src.contexts.world.domain.entities import (
    ClimateType,
    EventOutcome,
    EventSignificance,
    EventType,
    Faction,
    FactionAlignment,
    FactionStatus,
    FactionType,
    HistoryEvent,
    Location,
    LocationStatus,
    LocationType,
    WorldSetting,
)

if TYPE_CHECKING:
    from src.contexts.knowledge.application.services.rag_integration_service import (
        RAGIntegrationService,
    )

logger = structlog.get_logger(__name__)


class LLMWorldGenerator(WorldGeneratorPort):
    """World generator using Gemini API.

    Implements the WorldGeneratorPort protocol to generate complete world lore
    using Google's Gemini large language model. The generator produces a
    WorldSetting, multiple Factions, Locations, and HistoryEvents in a single
    API call, maintaining cross-references between entities.

    Warzone 4 Integration:
        Optionally uses RAG (Retrieval-Augmented Generation) to enrich
        dialogue and beat suggestions with relevant context from the knowledge
        base. When a RAGIntegrationService is provided, the generator will
        retrieve relevant character, lore, and scene information to inform
        its outputs.

    Attributes:
        _model: Gemini model name (e.g., "gemini-2.0-flash").
        _temperature: Generation temperature controlling creativity (0-2).
        _prompt_path: Path to the YAML file containing system prompts.
        _api_key: Gemini API authentication key.
        _base_url: Gemini API endpoint URL.
        _rag_service: Optional RAG integration service for context enrichment.

    Example:
        >>> generator = LLMWorldGenerator(model="gemini-2.0-flash", temperature=0.7)
        >>> result = generator.generate(WorldGenerationInput(genre=Genre.FANTASY))
        >>> print(f"Generated {result.total_entities} entities")

        >>> # With RAG integration
        >>> from src.contexts.knowledge.application.services import RAGIntegrationService
        >>> rag_service = RAGIntegrationService.create(...)
        >>> generator_with_rag = LLMWorldGenerator(rag_service=rag_service)
        >>> dialogue = generator_with_rag.generate_dialogue(...)
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.8,
        prompt_path: Path | None = None,
        rag_service: RAGIntegrationService | None = None,
    ) -> None:
        """Initialize the LLM world generator.

        Args:
            model: Gemini model name (defaults to env GEMINI_MODEL)
            temperature: Generation temperature (0-2)
            prompt_path: Path to prompt YAML file
            rag_service: Optional RAG integration service for context enrichment
        """
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._temperature = temperature
        self._prompt_path = prompt_path or (
            Path(__file__).resolve().parents[1] / "prompts" / "world_gen.yaml"
        )
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._base_url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self._model}:generateContent"
        )
        self._rag_service = rag_service

    def generate(self, request: WorldGenerationInput) -> WorldGenerationResult:
        """Generate a complete world using the Gemini API.

        Args:
            request: Input parameters for world generation

        Returns:
            WorldGenerationResult containing all generated entities
        """
        log = logger.bind(
            genre=request.genre.value,
            era=request.era.value,
            tone=request.tone.value,
        )
        log.info("Starting world generation")

        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(request)

        try:
            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_and_build(response_text, request)
            log.info(
                "World generation completed",
                total_entities=result.total_entities,
            )
            return result
        except Exception as exc:
            log.error("World generation failed", error=str(exc))
            return self._error_result(request, str(exc))

    def _load_system_prompt(self) -> str:
        """Load the system prompt from YAML file.

        Reads the world_gen.yaml prompt template that instructs the LLM
        on the expected JSON output format and world-building guidelines.

        Returns:
            The system prompt string.

        Raises:
            ValueError: If system_prompt key is missing in the YAML file.
            FileNotFoundError: If the prompt file doesn't exist.
        """
        with self._prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in world_gen.yaml")
        return prompt

    def _build_user_prompt(self, request: WorldGenerationInput) -> str:
        """Build the user prompt from the request parameters.

        Constructs a structured prompt containing all world generation
        parameters including genre, era, tone, and generation targets.

        Args:
            request: Input parameters for world generation.

        Returns:
            Formatted user prompt string for the LLM.
        """
        themes_str = ", ".join(request.themes) if request.themes else "unspecified"
        constraints = request.custom_constraints or "None"

        return f"""Generate a complete world with the following parameters:

WORLD PARAMETERS:
- Genre: {request.genre.value}
- Era: {request.era.value}
- Tone: {request.tone.value}
- Themes: {themes_str}
- Magic Level: {request.magic_level}/10
- Technology Level: {request.technology_level}/10

GENERATION TARGETS:
- Number of Factions: {request.num_factions}
- Number of Locations: {request.num_locations}
- Number of Historical Events: {request.num_events}

ADDITIONAL CONSTRAINTS:
{constraints}

Return valid JSON only with the exact structure specified in the system prompt.
Use temp_id values (temp_faction_1, temp_location_1, etc.) for cross-references."""

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini API to generate world content.

        Sends the combined system and user prompts to the Gemini API
        and returns the raw text response.

        Args:
            system_prompt: Instructions for the LLM on output format.
            user_prompt: World generation parameters and constraints.

        Returns:
            Raw text response from the Gemini API.

        Raises:
            RuntimeError: If API key is missing, authentication fails,
                rate limit is exceeded, or other API errors occur.
        """
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        request_body = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": 8000,
            },
        }

        response = requests.post(
            self._base_url,
            headers=headers,
            json=request_body,
            timeout=120,
        )

        if response.status_code == 401:
            raise RuntimeError("Gemini API authentication failed - check GEMINI_API_KEY")
        elif response.status_code == 429:
            raise RuntimeError("Gemini API rate limit exceeded")
        elif response.status_code != 200:
            raise RuntimeError(
                f"Gemini API error {response.status_code}: {response.text}"
            )

        try:
            response_json = response.json()
            content = response_json["candidates"][0]["content"]["parts"][0]["text"]
            return content
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Failed to parse Gemini response: {e}")

    def _parse_and_build(
        self, content: str, request: WorldGenerationInput
    ) -> WorldGenerationResult:
        """Parse the LLM response and build domain entities.

        Extracts JSON from the response and constructs domain entities
        including WorldSetting, Factions, Locations, and HistoryEvents.

        Args:
            content: Raw text response from the LLM.
            request: Original generation request for fallback values.

        Returns:
            WorldGenerationResult containing all parsed entities.

        Raises:
            json.JSONDecodeError: If no valid JSON can be extracted.
        """
        payload = self._extract_json(content)
        return self._build_result(payload, request)

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from the response content.

        Attempts multiple strategies to extract valid JSON from the LLM
        response: direct parsing, markdown code block extraction, and
        embedded JSON object detection.

        Args:
            content: Raw text that may contain JSON.

        Returns:
            Parsed JSON as a dictionary.

        Raises:
            json.JSONDecodeError: If no valid JSON can be found.
        """
        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                return json.loads(content[start:end].strip())

        # Try to find JSON object in content
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start : end + 1])

        raise json.JSONDecodeError("No valid JSON found in response", content, 0)

    def _build_result(
        self, payload: Dict[str, Any], request: WorldGenerationInput
    ) -> WorldGenerationResult:
        """Build WorldGenerationResult from parsed JSON payload.

        Constructs domain entities in the correct order to resolve
        cross-references: locations first (needed by factions), then
        factions (needed by events), then events with full resolution.

        Args:
            payload: Parsed JSON containing world_setting, factions,
                locations, and events arrays.
            request: Original generation request for default values.

        Returns:
            Complete WorldGenerationResult with all entities.
        """
        # Build WorldSetting
        world_data = payload.get("world_setting", {})
        world_setting = self._build_world_setting(world_data, request)

        # Build Locations first (factions may reference them)
        locations_data = payload.get("locations", [])
        locations, location_id_map = self._build_locations(locations_data)

        # Build Factions (may reference locations)
        factions_data = payload.get("factions", [])
        factions, faction_id_map = self._build_factions(factions_data, location_id_map)

        # Build HistoryEvents (may reference both)
        events_data = payload.get("events", [])
        events = self._build_events(events_data, location_id_map, faction_id_map)

        # Generate summary
        summary = (
            f"Generated {world_setting.name}: "
            f"{len(factions)} factions, {len(locations)} locations, {len(events)} events"
        )

        return WorldGenerationResult(
            world_setting=world_setting,
            factions=factions,
            locations=locations,
            events=events,
            generation_summary=summary,
        )

    def _build_world_setting(
        self, data: Dict[str, Any], request: WorldGenerationInput
    ) -> WorldSetting:
        """Build WorldSetting entity from parsed data.

        Args:
            data: Dictionary containing world_setting fields from LLM.
            request: Original request providing genre, era, tone defaults.

        Returns:
            Constructed WorldSetting entity.
        """
        return WorldSetting(
            name=str(data.get("name", "Generated World")),
            description=str(data.get("description", "")),
            genre=request.genre,
            era=request.era,
            themes=data.get("themes", request.themes) or [],
            tone=request.tone,
            magic_level=request.magic_level,
            technology_level=request.technology_level,
            world_rules=data.get("world_rules", []) or [],
            cultural_influences=data.get("cultural_influences", []) or [],
        )

    def _build_locations(
        self, data: List[Dict[str, Any]]
    ) -> tuple[List[Location], Dict[str, str]]:
        """Build Location entities and return ID mapping.

        Creates Location entities from parsed data and builds a mapping
        from temporary IDs (used by LLM for cross-references) to actual
        UUIDs. Also resolves parent/child and connection relationships.

        Args:
            data: List of location dictionaries from LLM output.

        Returns:
            Tuple of (list of Location entities, temp_id to UUID mapping).
        """
        locations: List[Location] = []
        id_map: Dict[str, str] = {}

        for item in data:
            temp_id = item.get("temp_id", f"temp_loc_{len(locations)}")
            location = Location(
                name=str(item.get("name", "Unknown Location")),
                description=str(item.get("description", "")),
                location_type=self._parse_enum(
                    LocationType, item.get("location_type"), LocationType.REGION
                ),
                climate=self._parse_enum(
                    ClimateType, item.get("climate"), ClimateType.TEMPERATE
                ),
                status=self._parse_enum(
                    LocationStatus, item.get("status"), LocationStatus.STABLE
                ),
                population=int(item.get("population", 0)),
                notable_features=item.get("notable_features", []) or [],
                resources=item.get("resources", []) or [],
                dangers=item.get("dangers", []) or [],
                accessibility=int(item.get("accessibility", 50)),
                wealth_level=int(item.get("wealth_level", 50)),
                magic_concentration=int(item.get("magic_concentration", 0)),
            )
            locations.append(location)
            id_map[temp_id] = location.id

        # Resolve parent/child relationships
        for i, item in enumerate(data):
            parent_temp_id = item.get("parent_location_id")
            if parent_temp_id and parent_temp_id in id_map:
                locations[i].parent_location_id = id_map[parent_temp_id]

            for child_temp_id in item.get("child_location_ids", []) or []:
                if child_temp_id in id_map:
                    locations[i].child_location_ids.append(id_map[child_temp_id])

            for conn_temp_id in item.get("connections", []) or []:
                if conn_temp_id in id_map:
                    locations[i].connections.append(id_map[conn_temp_id])

        return locations, id_map

    def _build_factions(
        self, data: List[Dict[str, Any]], location_id_map: Dict[str, str]
    ) -> tuple[List[Faction], Dict[str, str]]:
        """Build Faction entities and return ID mapping.

        Creates Faction entities from parsed data, resolving location
        references (headquarters, territories) using the location ID map.

        Args:
            data: List of faction dictionaries from LLM output.
            location_id_map: Mapping from temp_id to Location UUID.

        Returns:
            Tuple of (list of Faction entities, temp_id to UUID mapping).
        """
        factions: List[Faction] = []
        id_map: Dict[str, str] = {}

        for item in data:
            temp_id = item.get("temp_id", f"temp_faction_{len(factions)}")

            # Resolve headquarters location
            hq_temp_id = item.get("headquarters_id")
            headquarters_id = location_id_map.get(hq_temp_id) if hq_temp_id else None

            # Resolve territories
            territories = []
            for terr_temp_id in item.get("territories", []) or []:
                if terr_temp_id in location_id_map:
                    territories.append(location_id_map[terr_temp_id])

            faction = Faction(
                name=str(item.get("name", "Unknown Faction")),
                description=str(item.get("description", "")),
                faction_type=self._parse_enum(
                    FactionType, item.get("faction_type"), FactionType.GUILD
                ),
                alignment=self._parse_enum(
                    FactionAlignment, item.get("alignment"), FactionAlignment.TRUE_NEUTRAL
                ),
                status=self._parse_enum(
                    FactionStatus, item.get("status"), FactionStatus.ACTIVE
                ),
                headquarters_id=headquarters_id,
                leader_name=item.get("leader_name"),
                founding_date=item.get("founding_date"),
                values=item.get("values", []) or [],
                goals=item.get("goals", []) or [],
                resources=item.get("resources", []) or [],
                influence=int(item.get("influence", 50)),
                military_strength=int(item.get("military_strength", 50)),
                economic_power=int(item.get("economic_power", 50)),
                member_count=int(item.get("member_count", 100)),
                territories=territories,
            )
            factions.append(faction)
            id_map[temp_id] = faction.id

        return factions, id_map

    def _build_events(
        self,
        data: List[Dict[str, Any]],
        location_id_map: Dict[str, str],
        faction_id_map: Dict[str, str],
    ) -> List[HistoryEvent]:
        """Build HistoryEvent entities with full reference resolution.

        Creates HistoryEvent entities from parsed data in two passes:
        first creating all events to get their UUIDs, then resolving
        event-to-event relationships (preceding, following, related).

        Args:
            data: List of event dictionaries from LLM output.
            location_id_map: Mapping from temp_id to Location UUID.
            faction_id_map: Mapping from temp_id to Faction UUID.

        Returns:
            List of HistoryEvent entities with resolved relationships.
        """
        events: List[HistoryEvent] = []
        event_id_map: Dict[str, str] = {}

        # First pass: create events
        for item in data:
            temp_id = item.get("temp_id", f"temp_event_{len(events)}")

            # Resolve location IDs
            location_ids = []
            for loc_temp_id in item.get("location_ids", []) or []:
                if loc_temp_id in location_id_map:
                    location_ids.append(location_id_map[loc_temp_id])

            # Resolve faction IDs
            faction_ids = []
            for fac_temp_id in item.get("faction_ids", []) or []:
                if fac_temp_id in faction_id_map:
                    faction_ids.append(faction_id_map[fac_temp_id])

            event = HistoryEvent(
                name=str(item.get("name", "Unknown Event")),
                description=str(item.get("description", "")),
                event_type=self._parse_enum(
                    EventType, item.get("event_type"), EventType.POLITICAL
                ),
                significance=self._parse_enum(
                    EventSignificance, item.get("significance"), EventSignificance.MODERATE
                ),
                outcome=self._parse_enum(
                    EventOutcome, item.get("outcome"), EventOutcome.NEUTRAL
                ),
                date_description=str(item.get("date_description", "Unknown date")),
                duration_description=item.get("duration_description"),
                location_ids=location_ids,
                faction_ids=faction_ids,
                key_figures=item.get("key_figures", []) or [],
                causes=item.get("causes", []) or [],
                consequences=item.get("consequences", []) or [],
                is_secret=bool(item.get("is_secret", False)),
                narrative_importance=int(item.get("narrative_importance", 50)),
            )
            events.append(event)
            event_id_map[temp_id] = event.id

        # Second pass: resolve event relationships
        for i, item in enumerate(data):
            for pre_temp_id in item.get("preceding_event_ids", []) or []:
                if pre_temp_id in event_id_map:
                    events[i].preceding_event_ids.append(event_id_map[pre_temp_id])

            for fol_temp_id in item.get("following_event_ids", []) or []:
                if fol_temp_id in event_id_map:
                    events[i].following_event_ids.append(event_id_map[fol_temp_id])

            for rel_temp_id in item.get("related_event_ids", []) or []:
                if rel_temp_id in event_id_map:
                    events[i].related_event_ids.append(event_id_map[rel_temp_id])

        return events

    def _parse_enum(self, enum_class: type, value: Any, default: Any) -> Any:
        """Parse a string value into an enum, returning default if invalid.

        Safely converts string values from LLM output to enum instances,
        handling None values and invalid strings gracefully.

        Args:
            enum_class: The enum type to convert to.
            value: String value to parse (or None).
            default: Default enum value if parsing fails.

        Returns:
            The parsed enum value or the default.
        """
        if value is None:
            return default
        if isinstance(value, enum_class):
            return value
        try:
            return enum_class(str(value).lower())
        except ValueError:
            return default

    def _error_result(
        self, request: WorldGenerationInput, reason: str
    ) -> WorldGenerationResult:
        """Return an error result when generation fails.

        Creates a minimal WorldGenerationResult with an error-state
        WorldSetting and empty entity lists, preserving the original
        request parameters.

        Args:
            request: Original generation request.
            reason: Error message describing the failure.

        Returns:
            WorldGenerationResult with error information.
        """
        error_world = WorldSetting(
            name="Generation Failed",
            description=f"World generation failed: {reason}",
            genre=request.genre,
            era=request.era,
            tone=request.tone,
            themes=request.themes,
            magic_level=request.magic_level,
            technology_level=request.technology_level,
        )
        return WorldGenerationResult(
            world_setting=error_world,
            factions=[],
            locations=[],
            events=[],
            generation_summary=f"Error: {reason}",
        )

    # ==================== RAG Integration Helpers ====================

    async def _enrich_with_rag(
        self,
        query: str,
        base_prompt: str,
    ) -> str:
        """Enrich a prompt with RAG context if available.

        Args:
            query: Search query for retrieving relevant context
            base_prompt: The base prompt to enrich

        Returns:
            Enriched prompt with RAG context, or original prompt if RAG unavailable
        """
        if self._rag_service is None:
            return base_prompt

        try:
            result = await self._rag_service.enrich_prompt(
                query=query,
                base_prompt=base_prompt,
            )
            logger.debug(
                "rag_enrichment",
                chunks_retrieved=result.chunks_retrieved,
                tokens_added=result.tokens_added,
            )
            return result.prompt
        except Exception as exc:
            logger.warning(
                "rag_enrichment_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return base_prompt

    def _extract_keywords_for_dialogue(
        self,
        character: "CharacterData",
        context: str,
        mood: Optional[str] | None,
    ) -> str:
        """Extract keywords from dialogue request for RAG query.

        Builds a search query combining character name, traits, and context
        to retrieve relevant knowledge base entries.

        Args:
            character: Character data for name and traits
            context: The dialogue context/situation
            mood: Optional current mood

        Returns:
            Search query string for RAG retrieval
        """
        parts = [character.name]

        if character.traits:
            parts.extend(character.traits[:3])  # Top 3 traits

        if mood:
            parts.append(mood)

        # Extract key phrases from context (simple extraction)
        context_words = context.split()[:5]  # First 5 words
        parts.extend(context_words)

        return " ".join(parts)

    def _extract_keywords_for_beats(
        self,
        current_beats: List[Dict[str, Any]],
        scene_context: str,
        mood_target: Optional[int] | None,
    ) -> str:
        """Extract keywords from beat request for RAG query.

        Args:
            current_beats: Existing beat sequence
            scene_context: Scene description
            mood_target: Optional target mood

        Returns:
            Search query string for RAG retrieval
        """
        parts = []

        # Add scene context keywords
        context_words = scene_context.split()[:8]
        parts.extend(context_words)

        # Add mood direction if specified
        if mood_target is not None:
            if mood_target > 0:
                parts.append("uplifting positive")
            elif mood_target < 0:
                parts.append("tense negative dramatic")

        # Add recent beat types for pattern matching
        if current_beats:
            recent_types = [b.get("beat_type", "") for b in current_beats[-3:]]
            parts.extend(recent_types)

        return " ".join(parts)

    # ==================== Dialogue Generation ====================

    async def generate_dialogue(
        self,
        character: "CharacterData",
        context: str,
        mood: Optional[str] = None,
        use_rag: bool = True,
    ) -> "DialogueResult":
        """Generate dialogue in character voice using psychology, traits, and speaking style.

        Creates character-authentic speech by injecting personality data into the
        prompt. The dialogue generator considers the Big Five psychology traits,
        character-specific traits, and speaking style to produce responses that
        sound like the character would naturally speak.

        RAG Integration (Warzone 4):
            When use_rag is True and a RAGIntegrationService is available,
            the generator retrieves relevant character knowledge, lore, and
            context from the knowledge base to inform the dialogue.

        Why this matters: Characters need consistent voices. A high-neuroticism
        character should hedge and worry, while a high-extraversion character
        should be enthusiastic and talkative. This method ensures AI-generated
        dialogue matches established character patterns.

        Args:
            character: CharacterData containing psychology, traits, and speaking_style.
                      This can be a Character aggregate or a simpler data structure.
            context: The situation or prompt the character is responding to.
                    Examples: "A stranger asks for directions", "Their rival insults them".
            mood: Optional current emotional state that modifies normal patterns.
                 Examples: "angry", "melancholic", "excited", "fearful".
            use_rag: Whether to use RAG for context enrichment (default: True).

        Returns:
            DialogueResult containing the generated dialogue, internal thought,
            tone, and optional body language.

        Example:
            >>> result = await generator.generate_dialogue(
            ...     character=my_character,
            ...     context="A merchant offers a suspiciously good deal",
            ...     mood="cautious"
            ... )
            >>> print(result.dialogue)
            "I've seen deals like this before. What's the catch?"
        """
        log = logger.bind(
            character_name=character.name,
            has_psychology=character.psychology is not None,
            mood=mood,
            has_rag=self._rag_service is not None and use_rag,
        )
        log.info("Starting dialogue generation")

        try:
            system_prompt = self._load_dialogue_prompt()
            base_user_prompt = self._build_dialogue_user_prompt(character, context, mood)

            # Enrich with RAG if enabled and available
            if use_rag and self._rag_service is not None:
                rag_query = self._extract_keywords_for_dialogue(character, context, mood)
                user_prompt = await self._enrich_with_rag(rag_query, base_user_prompt)
            else:
                user_prompt = base_user_prompt

            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_dialogue_response(response_text)

            log.info("Dialogue generation completed", tone=result.tone)
            return result

        except Exception as exc:
            log.error("Dialogue generation failed", error=str(exc))
            return DialogueResult(
                dialogue="...",
                tone="uncertain",
                error=str(exc),
            )

    def _load_dialogue_prompt(self) -> str:
        """Load the dialogue generation system prompt from YAML file.

        Returns:
            The system prompt string for dialogue generation.

        Raises:
            ValueError: If system_prompt key is missing in the YAML file.
            FileNotFoundError: If the prompt file doesn't exist.
        """
        dialogue_prompt_path = (
            Path(__file__).resolve().parents[1] / "prompts" / "dialogue_gen.yaml"
        )
        with dialogue_prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in dialogue_gen.yaml")
        return prompt

    def _build_dialogue_user_prompt(
        self,
        character: "CharacterData",
        context: str,
        mood: Optional[str],
    ) -> str:
        """Build the user prompt for dialogue generation.

        Injects the character's psychology, traits, and speaking style into
        a structured prompt that guides the LLM to produce authentic dialogue.

        Args:
            character: CharacterData with personality information.
            context: The situation the character is responding to.
            mood: Optional current emotional state.

        Returns:
            Formatted user prompt string.
        """
        # Build psychology section
        psychology_section = "Not specified"
        if character.psychology:
            psych = character.psychology
            psychology_section = f"""Openness: {psych.get('openness', 50)}/100
Conscientiousness: {psych.get('conscientiousness', 50)}/100
Extraversion: {psych.get('extraversion', 50)}/100
Agreeableness: {psych.get('agreeableness', 50)}/100
Neuroticism: {psych.get('neuroticism', 50)}/100"""

        # Build traits section
        traits_section = "None specified"
        if character.traits:
            traits_section = ", ".join(character.traits)

        # Build speaking style section
        speaking_style = character.speaking_style or "Natural, conversational"

        # Build mood section
        mood_section = mood or "Neutral"

        return f"""Generate dialogue for this character:

CHARACTER NAME: {character.name}

PSYCHOLOGY (Big Five):
{psychology_section}

CHARACTER TRAITS:
{traits_section}

SPEAKING STYLE:
{speaking_style}

CURRENT MOOD:
{mood_section}

CONTEXT/SITUATION:
{context}

Generate a response that this character would naturally give in this situation.
Return valid JSON only with the exact structure specified in the system prompt."""

    def _parse_dialogue_response(self, content: str) -> "DialogueResult":
        """Parse the LLM response into a DialogueResult.

        Args:
            content: Raw text response from the LLM.

        Returns:
            DialogueResult with parsed dialogue data.
        """
        payload = self._extract_json(content)

        return DialogueResult(
            dialogue=str(payload.get("dialogue", "...")),
            internal_thought=payload.get("internal_thought"),
            tone=str(payload.get("tone", "neutral")),
            body_language=payload.get("body_language"),
        )

    # ==================== Relationship History Generation ====================

    def generate_relationship_history(
        self,
        character_a: "CharacterData",
        character_b: "CharacterData",
        trust: int = 50,
        romance: int = 0,
    ) -> "RelationshipHistoryResult":
        """Generate backstory explaining the relationship between two characters.

        Creates a compelling narrative that explains how the two characters came
        to have their current trust and romance levels. The generated history
        includes their first meeting, defining moments, and current status.

        Why this matters: Every significant relationship in a narrative needs
        depth and history. Rather than requiring writers to manually create
        backstories for every character pair, this method infers plausible
        histories from the current relationship metrics.

        Args:
            character_a: First character in the relationship.
            character_b: Second character in the relationship.
            trust: Current trust level between them (0-100). Default 50 is neutral.
            romance: Current romance level between them (0-100). Default 0 is none.

        Returns:
            RelationshipHistoryResult containing the generated backstory,
            first meeting, defining moment, and current status.

        Example:
            >>> result = generator.generate_relationship_history(
            ...     character_a=hero_data,
            ...     character_b=mentor_data,
            ...     trust=85,
            ...     romance=0
            ... )
            >>> print(result.backstory)
            "They first met when Marcus saved Elena from bandits..."
        """
        log = logger.bind(
            character_a=character_a.name,
            character_b=character_b.name,
            trust=trust,
            romance=romance,
        )
        log.info("Starting relationship history generation")

        try:
            system_prompt = self._load_relationship_history_prompt()
            user_prompt = self._build_relationship_history_user_prompt(
                character_a, character_b, trust, romance
            )

            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_relationship_history_response(response_text)

            log.info("Relationship history generation completed")
            return result

        except Exception as exc:
            log.error("Relationship history generation failed", error=str(exc))
            return RelationshipHistoryResult(
                backstory="Unable to generate relationship history.",
                error=str(exc),
            )

    def _load_relationship_history_prompt(self) -> str:
        """Load the relationship history generation system prompt from YAML file.

        Returns:
            The system prompt string for relationship history generation.

        Raises:
            ValueError: If system_prompt key is missing in the YAML file.
            FileNotFoundError: If the prompt file doesn't exist.
        """
        prompt_path = (
            Path(__file__).resolve().parents[1]
            / "prompts"
            / "relationship_history_gen.yaml"
        )
        with prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in relationship_history_gen.yaml")
        return prompt

    def _build_relationship_history_user_prompt(
        self,
        character_a: "CharacterData",
        character_b: "CharacterData",
        trust: int,
        romance: int,
    ) -> str:
        """Build the user prompt for relationship history generation.

        Injects both characters' information and current relationship metrics
        into a structured prompt that guides the LLM to produce a coherent
        backstory explaining their relationship dynamics.

        Args:
            character_a: First character data.
            character_b: Second character data.
            trust: Current trust level (0-100).
            romance: Current romance level (0-100).

        Returns:
            Formatted user prompt string.
        """

        def format_character_section(char: "CharacterData", label: str) -> str:
            """Format a single character's information for the prompt."""
            # Build psychology section
            psychology_section = "Not specified"
            if char.psychology:
                psych = char.psychology
                psychology_section = (
                    f"Openness: {psych.get('openness', 50)}, "
                    f"Conscientiousness: {psych.get('conscientiousness', 50)}, "
                    f"Extraversion: {psych.get('extraversion', 50)}, "
                    f"Agreeableness: {psych.get('agreeableness', 50)}, "
                    f"Neuroticism: {psych.get('neuroticism', 50)}"
                )

            # Build traits section
            traits_section = "None specified"
            if char.traits:
                traits_section = ", ".join(char.traits)

            return f"""{label}:
  Name: {char.name}
  Psychology (Big Five): {psychology_section}
  Traits: {traits_section}"""

        char_a_section = format_character_section(character_a, "CHARACTER A")
        char_b_section = format_character_section(character_b, "CHARACTER B")

        return f"""Generate a relationship history for these two characters:

{char_a_section}

{char_b_section}

CURRENT RELATIONSHIP METRICS:
  Trust Level: {trust}/100
  Romance Level: {romance}/100

Based on these personalities and their current trust/romance levels, create a
backstory that explains how they got to this point. Consider their psychology
and traits when determining what conflicts or connections would naturally arise.

Return valid JSON only with the exact structure specified in the system prompt."""

    def _parse_relationship_history_response(
        self, content: str
    ) -> "RelationshipHistoryResult":
        """Parse the LLM response into a RelationshipHistoryResult.

        Args:
            content: Raw text response from the LLM.

        Returns:
            RelationshipHistoryResult with parsed backstory data.
        """
        payload = self._extract_json(content)

        return RelationshipHistoryResult(
            backstory=str(payload.get("backstory", "Unable to generate backstory.")),
            first_meeting=payload.get("first_meeting"),
            defining_moment=payload.get("defining_moment"),
            current_status=payload.get("current_status"),
        )

    # ==================== Beat Suggestion Generation ====================

    async def suggest_next_beats(
        self,
        current_beats: List[Dict[str, Any]],
        scene_context: str,
        mood_target: Optional[int] = None,
        use_rag: bool = True,
    ) -> "BeatSuggestionResult":
        """Suggest next beats for a scene based on current sequence and context.

        Breaks writer's block by generating 3 AI-suggested beats that could
        logically follow the current beat sequence. Considers the scene context,
        current beat types, and desired mood trajectory.

        RAG Integration (Warzone 4):
            When use_rag is True and a RAGIntegrationService is available,
            the generator retrieves relevant scene patterns, narrative conventions,
            and story context to inform beat suggestions.

        Why this matters: Writers often struggle with "what happens next?"
        This method provides creative sparks while respecting the established
        narrative flow and emotional pacing.

        Args:
            current_beats: List of existing beats with 'beat_type', 'content',
                          and optionally 'mood_shift' keys. Can be empty.
            scene_context: Description of the scene including setting, characters
                          involved, and current situation/goals.
            mood_target: Optional target mood level (-5 to +5) for the scene's
                        direction. If None, suggestions maintain current mood.
            use_rag: Whether to use RAG for context enrichment (default: True).

        Returns:
            BeatSuggestionResult containing 3 suggestions with beat_type,
            content, mood_shift, and rationale.

        Example:
            >>> result = await generator.suggest_next_beats(
            ...     current_beats=[
            ...         {"beat_type": "action", "content": "She drew her sword."},
            ...         {"beat_type": "dialogue", "content": "'Stay back!' she warned."},
            ...     ],
            ...     scene_context="A tense standoff in an abandoned warehouse between
            ...                   the hero and a mysterious figure blocking her path.",
            ...     mood_target=-2  # Building tension
            ... )
            >>> print(result.suggestions[0].content)
        """
        log = logger.bind(
            num_current_beats=len(current_beats),
            has_mood_target=mood_target is not None,
            has_rag=self._rag_service is not None and use_rag,
        )
        log.info("Starting beat suggestion generation")

        try:
            system_prompt = self._load_beat_suggester_prompt()
            base_user_prompt = self._build_beat_suggester_user_prompt(
                current_beats, scene_context, mood_target
            )

            # Enrich with RAG if enabled and available
            if use_rag and self._rag_service is not None:
                rag_query = self._extract_keywords_for_beats(
                    current_beats, scene_context, mood_target
                )
                user_prompt = await self._enrich_with_rag(rag_query, base_user_prompt)
            else:
                user_prompt = base_user_prompt

            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_beat_suggestion_response(response_text)

            log.info(
                "Beat suggestion generation completed",
                num_suggestions=len(result.suggestions),
            )
            return result

        except Exception as exc:
            log.error("Beat suggestion generation failed", error=str(exc))
            return BeatSuggestionResult(
                suggestions=[],
                error=str(exc),
            )

    def _load_beat_suggester_prompt(self) -> str:
        """Load the beat suggester system prompt from YAML file.

        Returns:
            The system prompt string for beat suggestion generation.

        Raises:
            ValueError: If system_prompt key is missing in the YAML file.
            FileNotFoundError: If the prompt file doesn't exist.
        """
        prompt_path = (
            Path(__file__).resolve().parents[1] / "prompts" / "beat_suggester.yaml"
        )
        with prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in beat_suggester.yaml")
        return prompt

    def _build_beat_suggester_user_prompt(
        self,
        current_beats: List[Dict[str, Any]],
        scene_context: str,
        mood_target: Optional[int],
    ) -> str:
        """Build the user prompt for beat suggestion generation.

        Constructs a detailed prompt containing the current beat sequence,
        scene context, and mood trajectory to guide the AI's suggestions.

        Args:
            current_beats: List of existing beats with type and content.
            scene_context: Description of the scene.
            mood_target: Optional target mood level.

        Returns:
            Formatted user prompt string.
        """
        # Build current beats section
        if current_beats:
            beats_section = ""
            for i, beat in enumerate(current_beats, 1):
                beat_type = beat.get("beat_type", "unknown")
                content = beat.get("content", "")
                mood = beat.get("mood_shift", 0)
                beats_section += f"{i}. [{beat_type.upper()}] (mood: {mood:+d}) {content}\n"
        else:
            beats_section = "No beats yet - this is the start of the scene."

        # Analyze beat type balance
        beat_types = [b.get("beat_type", "").lower() for b in current_beats]
        action_count = sum(1 for t in beat_types if t in ("action", "transition"))
        reaction_count = sum(1 for t in beat_types if t in ("reaction", "dialogue"))

        if action_count > reaction_count + 1:
            balance_hint = "The scene is heavy on action - consider a reaction or dialogue."
        elif reaction_count > action_count + 1:
            balance_hint = "The scene is heavy on reaction/dialogue - consider an action."
        else:
            balance_hint = "The action/reaction balance is good."

        # Calculate current mood trajectory
        if current_beats:
            mood_shifts = [b.get("mood_shift", 0) for b in current_beats]
            current_mood = sum(mood_shifts)
            mood_trend = "upward" if current_mood > 0 else "downward" if current_mood < 0 else "neutral"
        else:
            current_mood = 0
            mood_trend = "neutral"

        # Build mood target section
        if mood_target is not None:
            mood_diff = mood_target - current_mood
            if mood_diff > 0:
                mood_direction = f"Aim for positive mood shifts (target: {mood_target:+d}, current: {current_mood:+d})"
            elif mood_diff < 0:
                mood_direction = f"Aim for negative mood shifts (target: {mood_target:+d}, current: {current_mood:+d})"
            else:
                mood_direction = f"Maintain current mood level ({current_mood:+d})"
        else:
            mood_direction = "Follow natural story momentum"

        return f"""Suggest 3 beats to continue this scene:

SCENE CONTEXT:
{scene_context}

CURRENT BEAT SEQUENCE:
{beats_section}

PACING ANALYSIS:
- Beat type balance: {balance_hint}
- Current mood trajectory: {mood_trend} (cumulative: {current_mood:+d})
- Mood target: {mood_direction}

Generate 3 suggested beats that could follow this sequence. Each suggestion should:
1. Logically follow from the current beats
2. Move toward the mood target
3. Serve the scene's dramatic purpose

Return valid JSON only with the exact structure specified in the system prompt."""

    def _parse_beat_suggestion_response(self, content: str) -> "BeatSuggestionResult":
        """Parse the LLM response into a BeatSuggestionResult.

        Args:
            content: Raw text response from the LLM.

        Returns:
            BeatSuggestionResult with parsed suggestions.
        """
        payload = self._extract_json(content)

        suggestions_data = payload.get("suggestions", [])
        suggestions = []

        for item in suggestions_data[:3]:  # Limit to 3 suggestions
            suggestion = BeatSuggestion(
                beat_type=str(item.get("beat_type", "action")).lower(),
                content=str(item.get("content", "")),
                mood_shift=int(item.get("mood_shift", 0)),
                rationale=item.get("rationale"),
            )
            # Clamp mood_shift to valid range
            suggestion.mood_shift = max(-5, min(5, suggestion.mood_shift))
            suggestions.append(suggestion)

        return BeatSuggestionResult(suggestions=suggestions)

    # ==================== Scene Critique Generation ====================

    def critique_scene(
        self,
        scene_text: str,
        scene_goals: Optional[List[str]] = None,
    ) -> "CritiqueResult":
        """Analyze scene quality across multiple craft dimensions.

        Provides AI-generated feedback on scene writing quality, evaluating
        pacing, narrative voice, showing vs. telling, and dialogue naturalism.
        Returns specific, actionable suggestions for improvement along with
        recognition of what works well.

        Why this matters: Writers need objective feedback beyond subjective
        impressions. The AI critique analyzes specific craft elements and
        provides actionable suggestions to elevate prose to professional
        standards, similar to a harsh but fair literary editor.

        Args:
            scene_text: The full text content of the scene to analyze.
            scene_goals: Optional list of writer's goals for the scene.
                        Examples: ["reveal character motivation", "build tension",
                        "establish setting", "advance plot"]. The critique will
                        evaluate how well the scene achieves these goals.

        Returns:
            CritiqueResult containing overall score (1-10), category-specific
            evaluations (pacing, voice, showing, dialogue), highlights of what
            works, summary assessment, and actionable suggestions.

        Example:
            >>> result = generator.critique_scene(
            ...     scene_text="The room was dark. John felt scared. "
            ...                "'Who's there?' he asked nervously.",
            ...     scene_goals=["build tension", "establish suspense"]
            ... )
            >>> print(result.summary)
            >>> # "The scene establishes suspense but relies on telling
            >>> #  emotions rather than showing them through action..."
        """
        log = logger.bind(
            scene_text_length=len(scene_text),
            has_scene_goals=scene_goals is not None,
        )
        log.info("Starting scene critique")

        try:
            system_prompt = self._load_critique_prompt()
            user_prompt = self._build_critique_user_prompt(scene_text, scene_goals)

            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_critique_response(response_text)

            log.info(
                "Scene critique completed",
                overall_score=result.overall_score,
                num_categories=len(result.category_scores),
            )
            return result

        except Exception as exc:
            log.error("Scene critique failed", error=str(exc))
            return CritiqueResult(
                overall_score=0,
                category_scores=[],
                highlights=[],
                summary="Unable to generate critique.",
                error=str(exc),
            )

    def _load_critique_prompt(self) -> str:
        """Load the scene critique system prompt from YAML file.

        Returns:
            The system prompt string for scene critique.

        Raises:
            ValueError: If system_prompt key is missing in the YAML file.
            FileNotFoundError: If the prompt file doesn't exist.
        """
        prompt_path = (
            Path(__file__).resolve().parents[1] / "prompts" / "scene_critique.yaml"
        )
        with prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in scene_critique.yaml")
        return prompt

    def _build_critique_user_prompt(
        self,
        scene_text: str,
        scene_goals: Optional[List[str]],
    ) -> str:
        """Build the user prompt for scene critique generation.

        Constructs a detailed prompt containing the scene text and optional
        writer goals, guiding the AI to provide targeted, actionable feedback.

        Args:
            scene_text: The full text content of the scene.
            scene_goals: Optional list of writer's goals for the scene.

        Returns:
            Formatted user prompt string.
        """
        # Truncate scene text if too long (max ~2000 words for context limit)
        max_length = 12000  # ~2000 words
        truncated_text = (
            scene_text[:max_length] + "..."
            if len(scene_text) > max_length
            else scene_text
        )

        # Build goals section
        if scene_goals:
            goals_section = "\n".join(f"- {goal}" for goal in scene_goals)
        else:
            goals_section = "No specific goals provided - evaluate general quality."

        return f"""Critique the following scene:

SCENE TEXT:
{truncated_text}

SCENE GOALS:
{goals_section}

Analyze this scene across the four quality dimensions (pacing, voice, showing, dialogue)
and provide specific, actionable feedback. Consider how well the scene achieves its
stated goals.

Return valid JSON only with the exact structure specified in the system prompt."""

    def _parse_critique_response(self, content: str) -> "CritiqueResult":
        """Parse the LLM response into a CritiqueResult.

        Args:
            content: Raw text response from the LLM.

        Returns:
            CritiqueResult with parsed critique data.
        """
        payload = self._extract_json(content)

        # Parse overall score
        overall_score = int(payload.get("overall_score", 5))
        overall_score = max(1, min(10, overall_score))  # Clamp to 1-10

        # Parse category scores
        category_scores_data = payload.get("category_scores", [])
        category_scores = []

        valid_categories = {"pacing", "voice", "showing", "dialogue"}

        for cat_data in category_scores_data:
            category = str(cat_data.get("category", "")).lower()
            # Normalize category names
            if category not in valid_categories:
                continue

            score = int(cat_data.get("score", 5))
            score = max(1, min(10, score))  # Clamp to 1-10

            issues = cat_data.get("issues", []) or []
            suggestions = cat_data.get("suggestions", []) or []

            # Ensure lists
            if not isinstance(issues, list):
                issues = []
            if not isinstance(suggestions, list):
                suggestions = []

            category_scores.append(
                CritiqueCategoryScore(
                    category=category,
                    score=score,
                    issues=issues,
                    suggestions=suggestions,
                )
            )

        # Parse highlights
        highlights_data = payload.get("highlights", []) or []
        if not isinstance(highlights_data, list):
            highlights_data = []
        highlights = [str(h) for h in highlights_data]

        # Parse summary
        summary = str(payload.get("summary", ""))

        return CritiqueResult(
            overall_score=overall_score,
            category_scores=category_scores,
            highlights=highlights,
            summary=summary,
        )


@dataclass
class BeatSuggestion:
    """A single beat suggestion from the AI.

    Represents one suggested narrative beat with its type, content, emotional
    impact, and the AI's reasoning for the suggestion.

    Attributes:
        beat_type: Classification of the beat (action, reaction, dialogue, etc.)
        content: The suggested narrative text (1-3 sentences).
        mood_shift: Emotional impact (-5 to +5).
        rationale: AI's explanation of why this beat fits.
    """

    beat_type: str
    content: str
    mood_shift: int = 0
    rationale: Optional[str] = None


@dataclass
class BeatSuggestionResult:
    """Result of beat suggestion generation.

    Contains 3 AI-generated beat suggestions that could follow the current
    sequence, along with optional error information.

    Why 3 suggestions:
        Offering multiple options gives writers creative choice while
        preventing paralysis from too many options. The suggestions represent
        different approaches: expected continuation, dramatic turn, and
        character-focused moment.

    Attributes:
        suggestions: List of 3 BeatSuggestion objects.
        error: Error message if generation failed.
    """

    suggestions: List[BeatSuggestion] = field(default_factory=list)
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "suggestions": [
                {
                    "beat_type": s.beat_type,
                    "content": s.content,
                    "mood_shift": s.mood_shift,
                    "rationale": s.rationale,
                }
                for s in self.suggestions
            ]
        }
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class CharacterData:
    """Data structure for character information needed by dialogue generation.

    This is a simple data transfer object that can be constructed from
    a Character aggregate or from API request data. It contains only the
    fields needed for dialogue generation.

    Why a separate class: The Character aggregate in the character context
    has complex validation and domain logic. For dialogue generation, we
    only need a subset of that data in a simple format.
    """

    name: str
    psychology: Optional[Dict[str, int]] = None
    traits: Optional[List[str]] = None
    speaking_style: Optional[str] = None

    @classmethod
    def from_character_aggregate(cls, character: Any) -> "CharacterData":
        """Create CharacterData from a Character aggregate.

        Args:
            character: A Character aggregate from the character context.

        Returns:
            CharacterData with extracted fields.
        """
        psychology_dict = None
        if hasattr(character, 'psychology') and character.psychology:
            psychology_dict = character.psychology.to_dict()

        traits_list = None
        if hasattr(character, 'profile') and character.profile:
            if hasattr(character.profile, 'traits') and character.profile.traits:
                traits_list = list(character.profile.traits)
            elif hasattr(character.profile, 'personality_traits'):
                # Fallback to personality_traits if traits not set
                pt = character.profile.personality_traits
                if hasattr(pt, 'quirks') and pt.quirks:
                    traits_list = list(pt.quirks)

        return cls(
            name=character.profile.name if hasattr(character, 'profile') else str(character),
            psychology=psychology_dict,
            traits=traits_list,
            speaking_style=None,  # Can be extended in future
        )


@dataclass
class DialogueResult:
    """Result of dialogue generation.

    Contains the generated dialogue along with optional metadata about
    the character's internal state and physical expression.

    Attributes:
        dialogue: The character's spoken words (1-3 sentences).
        internal_thought: What the character thinks but doesn't say.
        tone: Emotional tone of the response (e.g., 'defensive', 'excited').
        body_language: Physical description (e.g., 'crosses arms').
        error: Error message if generation failed.
    """

    dialogue: str
    tone: str = "neutral"
    internal_thought: Optional[str] = None
    body_language: Optional[str] = None
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "dialogue": self.dialogue,
            "tone": self.tone,
        }
        if self.internal_thought:
            result["internal_thought"] = self.internal_thought
        if self.body_language:
            result["body_language"] = self.body_language
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class RelationshipHistoryResult:
    """Result of relationship history generation.

    Contains the generated backstory along with structured elements that
    explain how two characters developed their current relationship dynamics.

    Why generate backstory: Relationships in narratives need depth. Rather than
    having writers manually create history for every character pair, the AI can
    infer plausible backstories from the current trust/romance metrics. This
    creates consistent, believable relationship histories on demand.

    Attributes:
        backstory: A 2-4 paragraph narrative explaining the relationship history.
        first_meeting: How the characters first encountered each other.
        defining_moment: The pivotal event that shaped their current dynamic.
        current_status: A summary of where they currently stand.
        error: Error message if generation failed.
    """

    backstory: str
    first_meeting: Optional[str] = None
    defining_moment: Optional[str] = None
    current_status: Optional[str] = None
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "backstory": self.backstory,
        }
        if self.first_meeting:
            result["first_meeting"] = self.first_meeting
        if self.defining_moment:
            result["defining_moment"] = self.defining_moment
        if self.current_status:
            result["current_status"] = self.current_status
        if self.error:
            result["error"] = self.error
        return result


@dataclass
class CritiqueCategoryScore:
    """A category-specific critique score.

    Represents evaluation of a single quality dimension (pacing, voice, showing,
    dialogue) with specific issues and suggestions.

    Attributes:
        category: The quality dimension being evaluated.
        score: Score from 1-10 for this category.
        issues: List of specific problems identified in this category.
        suggestions: List of actionable improvements for this category.
    """

    category: str
    score: int
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class CritiqueResult:
    """Result of scene critique analysis.

    Contains AI-generated feedback on scene quality across multiple dimensions.
    Provides category-specific scores, overall assessment, highlights of what
    works, and actionable suggestions for improvement.

    Why scene critique:
        Writers need objective feedback on their work beyond subjective
        impressions. The AI critique analyzes specific craft elements like
        pacing, voice, showing vs. telling, and dialogue quality, providing
        actionable suggestions to elevate prose to professional standards.

    Attributes:
        overall_score: Overall quality score from 1-10.
        category_scores: List of category-specific evaluations.
        highlights: What works well in the scene.
        summary: Brief 2-3 sentence assessment.
        error: Error message if critique failed.
    """

    overall_score: int
    category_scores: List[CritiqueCategoryScore] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    summary: str = ""
    error: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this result represents an error."""
        return self.error is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API responses."""
        result: Dict[str, Any] = {
            "overall_score": self.overall_score,
            "category_scores": [
                {
                    "category": cat.category,
                    "score": cat.score,
                    "issues": cat.issues,
                    "suggestions": cat.suggestions,
                }
                for cat in self.category_scores
            ],
            "highlights": self.highlights,
            "summary": self.summary,
        }
        if self.error:
            result["error"] = self.error
        return result
