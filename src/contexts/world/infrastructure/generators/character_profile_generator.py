"""LLM-based character profile generator.

This module implements a character profile generator that uses LLM APIs
to generate detailed character profiles matching the CharacterProfile schema.
It supports both real LLM generation and mock mode for testing.

Typical usage example:
    >>> from src.contexts.world.infrastructure.generators import CharacterProfileGenerator
    >>> generator = CharacterProfileGenerator()
    >>> profile = generator.generate_character_profile(
    ...     name="Kira Darkwood",
    ...     archetype="Rogue",
    ...     context="A shadowy figure from the thieves' guild"
    ... )
    >>> print(profile.aliases)  # ["Shadow Blade", "The Whisper"]
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Protocol

import requests
import structlog
import yaml

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CharacterProfileInput:
    """Input parameters for character profile generation.

    Attributes:
        name: The character's primary name.
        archetype: The character archetype (e.g., "Hero", "Villain", "Mentor").
        context: Additional context about the character's background or world.
    """

    name: str
    archetype: str
    context: str = ""


@dataclass(frozen=True)
class CharacterProfileResult:
    """Result of character profile generation.

    Contains the generated profile fields that match the CharacterProfile
    value object's new fields from WORLD-001.

    Attributes:
        name: The character's name (may be refined by LLM).
        aliases: List of alternative names or nicknames.
        archetype: The character's narrative archetype.
        traits: List of personality traits.
        appearance: Physical description of the character.
        backstory: Brief character backstory.
        motivations: List of character motivations.
        quirks: Notable quirks or habits.
    """

    name: str
    aliases: List[str]
    archetype: str
    traits: List[str]
    appearance: str
    backstory: str
    motivations: List[str]
    quirks: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format.

        Returns:
            Dictionary representation of the profile result.
        """
        return {
            "name": self.name,
            "aliases": self.aliases,
            "archetype": self.archetype,
            "traits": self.traits,
            "appearance": self.appearance,
            "backstory": self.backstory,
            "motivations": self.motivations,
            "quirks": self.quirks,
        }


class CharacterProfileGeneratorPort(Protocol):
    """Protocol for character profile generators.

    This protocol defines the interface that all character profile generators
    must implement, enabling dependency injection and testing with mocks.
    """

    def generate_character_profile(
        self, name: str, archetype: str, context: str = ""
    ) -> CharacterProfileResult:
        """Generate a complete character profile from input parameters.

        Args:
            name: The character's primary name.
            archetype: The character archetype (Hero, Villain, Mentor, etc.).
            context: Additional context about the character's world or background.

        Returns:
            CharacterProfileResult containing the generated profile data.
        """
        ...


def _get_mock_profile(name: str, archetype: str) -> CharacterProfileResult:
    """Generate a deterministic mock profile for testing.

    This function provides predictable mock data based on the archetype,
    enabling testing without LLM API calls.

    Args:
        name: The character's primary name.
        archetype: The character archetype to use for template selection.

    Returns:
        CharacterProfileResult with mock data appropriate for the archetype.
    """
    archetype_key = archetype.strip().lower()

    templates: Dict[str, Dict[str, Any]] = {
        "hero": {
            "aliases": ["The Lightbringer", "Champion of the Dawn"],
            "traits": ["courageous", "selfless", "determined", "honorable"],
            "appearance": (
                "Tall and well-built with confident posture. "
                "Eyes gleam with inner resolve. Wears practical armor "
                "with subtle heroic embellishments."
            ),
            "backstory": (
                "Rose from humble origins after witnessing injustice firsthand. "
                "Trained under a renowned mentor before embarking on their quest."
            ),
            "motivations": ["protect the innocent", "right past wrongs", "find redemption"],
            "quirks": ["always helps those in need", "never breaks a promise"],
        },
        "villain": {
            "aliases": ["The Dark Tyrant", "Lord of Shadows"],
            "traits": ["ruthless", "calculating", "charismatic", "ambitious"],
            "appearance": (
                "Imposing figure cloaked in darkness. Sharp features "
                "with piercing eyes that seem to see through deception. "
                "Adorned with symbols of their dark power."
            ),
            "backstory": (
                "Once a respected figure, twisted by betrayal and loss. "
                "Now seeks to reshape the world according to their vision."
            ),
            "motivations": ["absolute power", "revenge on betrayers", "create order through fear"],
            "quirks": ["speaks in measured tones", "collects trophies from fallen foes"],
        },
        "mentor": {
            "aliases": ["The Sage", "Keeper of Ancient Ways"],
            "traits": ["wise", "patient", "cryptic", "protective"],
            "appearance": (
                "Weathered features that speak of long experience. "
                "Gentle eyes that hold depths of knowledge. "
                "Simple robes belie hidden power."
            ),
            "backstory": (
                "Has walked many paths and learned from countless trials. "
                "Now seeks to pass on wisdom to the next generation."
            ),
            "motivations": ["guide the worthy", "preserve ancient knowledge", "prevent past mistakes"],
            "quirks": ["speaks in riddles", "appears when least expected"],
        },
        "rogue": {
            "aliases": ["Shadow Dancer", "The Ghost"],
            "traits": ["cunning", "charming", "resourceful", "independent"],
            "appearance": (
                "Lithe and agile with quick, graceful movements. "
                "Unremarkable features that blend into any crowd. "
                "Clothing designed for stealth and practicality."
            ),
            "backstory": (
                "Learned to survive on the streets from a young age. "
                "Trust is hard-earned, but loyalty once given is absolute."
            ),
            "motivations": ["freedom", "wealth", "protect street family"],
            "quirks": ["fidgets with coins", "always knows the exits"],
        },
        "warrior": {
            "aliases": ["Ironside", "The Unbroken"],
            "traits": ["brave", "loyal", "fierce", "disciplined"],
            "appearance": (
                "Muscular build hardened by countless battles. "
                "Numerous scars tell stories of past conflicts. "
                "Carries weapons like extensions of their body."
            ),
            "backstory": (
                "Trained from youth in the warrior traditions. "
                "Has fought in many campaigns and lost many comrades."
            ),
            "motivations": ["glory in battle", "protect comrades", "die with honor"],
            "quirks": ["sharpens weapons constantly", "never sits with back to door"],
        },
    }

    template = templates.get(
        archetype_key,
        {
            "aliases": [f"{name} the Unknown", "The Mysterious One"],
            "traits": ["enigmatic", "adaptable", "observant"],
            "appearance": (
                "Average build with nondescript features. "
                "Something about them defies easy categorization."
            ),
            "backstory": "Origins shrouded in mystery.",
            "motivations": ["unknown goals", "hidden agenda"],
            "quirks": ["rarely speaks of the past"],
        },
    )

    return CharacterProfileResult(
        name=name,
        aliases=list(template["aliases"]),
        archetype=archetype,
        traits=list(template["traits"]),
        appearance=str(template["appearance"]),
        backstory=str(template["backstory"]),
        motivations=list(template["motivations"]),
        quirks=list(template["quirks"]),
    )


class MockCharacterProfileGenerator:
    """Deterministic character profile generator for testing.

    Uses predefined templates to generate consistent profile data
    without making LLM API calls. Useful for unit tests and development.
    """

    def generate_character_profile(
        self, name: str, archetype: str, context: str = ""
    ) -> CharacterProfileResult:
        """Generate a mock character profile.

        Args:
            name: The character's primary name.
            archetype: The character archetype for template selection.
            context: Ignored in mock mode but accepted for interface compatibility.

        Returns:
            CharacterProfileResult with deterministic mock data.
        """
        return _get_mock_profile(name, archetype)


class LLMCharacterProfileGenerator:
    """Character profile generator using Gemini API.

    Generates detailed character profiles by sending prompts to Google's
    Gemini LLM and parsing the structured JSON response.

    Attributes:
        _model: Gemini model name (e.g., "gemini-2.0-flash").
        _temperature: Generation temperature controlling creativity (0-2).
        _prompt_path: Path to the YAML file containing system prompts.
        _api_key: Gemini API authentication key.
        _base_url: Gemini API endpoint URL.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.8,
        prompt_path: Path | None = None,
    ) -> None:
        """Initialize the LLM character profile generator.

        Args:
            model: Gemini model name (defaults to env GEMINI_MODEL).
            temperature: Generation temperature (0-2), higher = more creative.
            prompt_path: Path to prompt YAML file.
        """
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._temperature = temperature
        self._prompt_path = prompt_path or (
            Path(__file__).resolve().parent / "character_profile_gen.yaml"
        )
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._base_url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self._model}:generateContent"
        )

    def generate_character_profile(
        self, name: str, archetype: str, context: str = ""
    ) -> CharacterProfileResult:
        """Generate a complete character profile using the Gemini API.

        Sends a structured prompt to the LLM and parses the JSON response
        into a CharacterProfileResult.

        Args:
            name: The character's primary name.
            archetype: The character archetype (Hero, Villain, Mentor, etc.).
            context: Additional context about the character's world or background.

        Returns:
            CharacterProfileResult containing the generated profile data.
        """
        log = logger.bind(name=name, archetype=archetype)
        log.info("Starting character profile generation")

        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(name, archetype, context)

        try:
            response_text = self._call_gemini(system_prompt, user_prompt)
            result = self._parse_response(response_text, name, archetype)
            log.info("Character profile generation completed")
            return result
        except Exception as exc:
            log.error("Character profile generation failed", error=str(exc))
            return self._error_result(name, archetype, str(exc))

    def _load_system_prompt(self) -> str:
        """Load the system prompt from YAML file.

        Returns:
            The system prompt string.

        Raises:
            ValueError: If system_prompt key is missing in the YAML file.
            FileNotFoundError: If the prompt file doesn't exist.
        """
        if not self._prompt_path.exists():
            # Use default prompt if file doesn't exist
            return self._default_system_prompt()

        with self._prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            return self._default_system_prompt()
        return prompt

    def _default_system_prompt(self) -> str:
        """Return the default system prompt for character profile generation.

        Returns:
            Default system prompt string.
        """
        return """You are a creative character profile generator for a narrative engine.
Generate detailed, consistent character profiles based on the given inputs.

Output MUST be valid JSON only with these exact keys:
- name: string (the character's primary name)
- aliases: array of 2-4 alternative names or nicknames
- archetype: string (the character's narrative role)
- traits: array of 4-6 personality traits (single words or short phrases)
- appearance: string (2-3 sentences describing physical appearance)
- backstory: string (2-3 sentences about their background)
- motivations: array of 2-4 core motivations
- quirks: array of 2-3 notable habits or quirks

Be creative but consistent. Traits should align with the archetype.
Do not include markdown formatting, code blocks, or commentary.
Return ONLY the JSON object."""

    def _build_user_prompt(self, name: str, archetype: str, context: str) -> str:
        """Build the user prompt from input parameters.

        Args:
            name: The character's primary name.
            archetype: The character archetype.
            context: Additional context about the character.

        Returns:
            Formatted user prompt string.
        """
        context_str = context.strip() if context else "A fantasy world setting"
        return f"""Generate a character profile with these inputs:

CHARACTER NAME: {name}
ARCHETYPE: {archetype}
CONTEXT: {context_str}

Return valid JSON only with the exact structure specified."""

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini API to generate character profile.

        Args:
            system_prompt: Instructions for the LLM on output format.
            user_prompt: Character generation parameters.

        Returns:
            Raw text response from the Gemini API.

        Raises:
            RuntimeError: If API key is missing or API call fails.
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
                "maxOutputTokens": 2000,
            },
        }

        response = requests.post(
            self._base_url,
            headers=headers,
            json=request_body,
            timeout=60,
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

    def _parse_response(
        self, content: str, name: str, archetype: str
    ) -> CharacterProfileResult:
        """Parse the LLM response into a CharacterProfileResult.

        Args:
            content: Raw text response from the LLM.
            name: Original character name for fallback.
            archetype: Original archetype for fallback.

        Returns:
            CharacterProfileResult with parsed data.
        """
        payload = self._extract_json(content)

        return CharacterProfileResult(
            name=str(payload.get("name", name)),
            aliases=self._ensure_list(payload.get("aliases", [])),
            archetype=str(payload.get("archetype", archetype)),
            traits=self._ensure_list(payload.get("traits", [])),
            appearance=str(payload.get("appearance", "")),
            backstory=str(payload.get("backstory", "")),
            motivations=self._ensure_list(payload.get("motivations", [])),
            quirks=self._ensure_list(payload.get("quirks", [])),
        )

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

    def _ensure_list(self, value: Any) -> List[str]:
        """Ensure a value is a list of strings.

        Args:
            value: Value to convert to list.

        Returns:
            List of strings.
        """
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            return [value]
        return []

    def _error_result(
        self, name: str, archetype: str, reason: str
    ) -> CharacterProfileResult:
        """Return an error result when generation fails.

        Args:
            name: Original character name.
            archetype: Original archetype.
            reason: Error message describing the failure.

        Returns:
            CharacterProfileResult with error placeholder data.
        """
        return CharacterProfileResult(
            name=name,
            aliases=["[Generation Error]"],
            archetype=archetype,
            traits=["error"],
            appearance=f"Character profile generation failed: {reason}",
            backstory="Unable to generate backstory due to an error.",
            motivations=["resolve generation error"],
            quirks=["appears glitchy"],
        )


class CharacterProfileGenerator:
    """Factory class for character profile generation.

    Automatically selects between LLM and mock generators based on
    environment configuration. Use MOCK_LLM=true to enable mock mode.

    Example:
        >>> generator = CharacterProfileGenerator()
        >>> profile = generator.generate_character_profile(
        ...     name="Elara Nightwind",
        ...     archetype="Rogue",
        ...     context="A thieves' guild in the city of shadows"
        ... )
    """

    def __init__(self, force_mock: bool = False) -> None:
        """Initialize the character profile generator.

        Args:
            force_mock: If True, always use mock generator regardless of env.
        """
        self._generator: CharacterProfileGeneratorPort
        use_mock = force_mock or os.getenv("MOCK_LLM", "").lower() in ("true", "1", "yes")

        if use_mock:
            self._generator = MockCharacterProfileGenerator()
            logger.info("Using mock character profile generator")
        else:
            self._generator = LLMCharacterProfileGenerator()
            logger.info("Using LLM character profile generator")

    def generate_character_profile(
        self, name: str, archetype: str, context: str = ""
    ) -> CharacterProfileResult:
        """Generate a complete character profile.

        Args:
            name: The character's primary name.
            archetype: The character archetype (Hero, Villain, Mentor, etc.).
            context: Additional context about the character's world or background.

        Returns:
            CharacterProfileResult containing the generated profile data.
        """
        return self._generator.generate_character_profile(name, archetype, context)


def generate_character_profile(
    name: str,
    archetype: str,
    context: str = "",
    generator: CharacterProfileGeneratorPort | None = None,
) -> CharacterProfileResult:
    """Convenience function to generate a character profile.

    This is the primary entry point for character profile generation.
    Uses the default generator unless one is explicitly provided.

    Args:
        name: The character's primary name.
        archetype: The character archetype (Hero, Villain, Mentor, etc.).
        context: Additional context about the character's world or background.
        generator: Optional generator implementation to use.

    Returns:
        CharacterProfileResult containing the generated profile data.

    Example:
        >>> profile = generate_character_profile(
        ...     name="Marcus Steelhand",
        ...     archetype="Warrior",
        ...     context="A veteran of the Northern Wars"
        ... )
        >>> print(profile.traits)  # ["brave", "loyal", "fierce", "disciplined"]
    """
    if generator is None:
        generator = CharacterProfileGenerator()
    return generator.generate_character_profile(name, archetype, context)
