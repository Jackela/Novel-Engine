#!/usr/bin/env python3
"""
ChroniclerAgent Core Implementation
==================================

This module implements the ChroniclerAgent class, which serves as the narrative
transcription system for the StoryForge AI Interactive Story Engine. The ChroniclerAgent
transforms structured campaign logs into dramatic narrative stories that capture
the essence of any fictional universe.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config.config_loader import get_config
from src.core.types.shared_types import CharacterAction
from src.core.event_bus import EventBus
from src.core.llm_service import LLMProvider, LLMRequest, ResponseFormat, UnifiedLLMService
from src.agents.persona_agent.agent import PersonaAgent
from src.prompts import (
    Language,
    PromptRegistry,
    PromptTemplate,
    StoryGenre,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STYLE_TEMPLATE_LIBRARY: Dict[str, Dict[str, str]] = {
    "sci_fi_dramatic": {
        "opening": (
            "In the vast cosmic hush of space surrounding Meridian Station, mission logs shimmer "
            "like constellations waiting to be translated into purpose, while consoles glow with "
            "patient telemetry and steady resolve."
        ),
        "segment": (
            "{character_focus} recorded {event_type} activity, weaving tension "
            "through starlit corridors and silent comms: {narrative}"
        ),
        "closing": (
            "Thus, another chapter concludes beneath auroras of ionized light, "
            "promising new voyages to anyone brave enough to read the stars and "
            "carry the mission onward."
        ),
    },
    "tactical": {
        "opening": (
            "Operational chronicle initiated. All units synchronize telemetry "
            "for high-fidelity playback."
        ),
        "segment": (
            "Turn {turn_number}: {character_focus} executed {event_type} with "
            "measured precision. Outcome: {narrative}"
        ),
        "closing": (
            "Log complete. Command relays recommend a measured debrief before the next sortie."
        ),
    },
    "philosophical": {
        "opening": (
            "Beyond the glow of nebulae, choices ripple like thought across an endless frontier."
        ),
        "segment": (
            "When {character_focus} embraced {event_type}, the cosmos murmured "
            "about consequence: {narrative}"
        ),
        "closing": (
            "Echoes of these decisions drift onward, inviting reflection amid the stars."
        ),
    },
}

GENERIC_FACTIONS = {
    "Galactic Defense Forces": "Frontier guardians maintaining peace along the rim.",
    "Colonial Guard": "Seasoned crews protecting vital colonies.",
    "Military Corps": "Joint task force specializing in rescue operations.",
    "Tech Guild": "Innovators who blend research with exploration.",
    "Alliance Forces": "Diplomatic escorts safeguarding interstellar accords.",
}

_SCRIPT_TAG_RE = re.compile(r"<\s*/?\s*script\b[^>]{0,1024}>", re.IGNORECASE)
_SQLI_RE = re.compile(r"drop\s+table", re.IGNORECASE)


def _sanitize_story(value: str) -> str:
    """Remove unsafe tags and obvious SQL payloads from generated prose."""
    text = value or ""
    text = _SCRIPT_TAG_RE.sub("", text)
    text = _SQLI_RE.sub("neutralized command", text)
    text = text.replace("\x00", "")
    return text.strip()


def _limit_story_length(text: str, max_length: int = 6000) -> str:
    """Keep narrative output within a reasonable upper bound."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text

    cutoff = max(text.rfind(".", 0, max_length), text.rfind("!", 0, max_length))
    cutoff = max(cutoff, text.rfind("?", 0, max_length))
    if cutoff < int(max_length * 0.7):
        return text[:max_length].rstrip()
    return text[: cutoff + 1].strip()


# Global LLM service instance (lazily initialized)
_llm_service: Optional[UnifiedLLMService] = None


def _get_llm_service() -> UnifiedLLMService:
    """Get or create the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = UnifiedLLMService()
    return _llm_service


def _make_gemini_api_request(prompt: str) -> Any:
    """
    Call Gemini API using the UnifiedLLMService.

    This function integrates with the production LLM service to generate
    high-quality narrative content using Google's Gemini 2.0 Flash model.

    Args:
        prompt: The prompt to send to the LLM

    Returns:
        The generated text response

    Raises:
        RuntimeError: If Gemini API is not configured
    """
    llm_service = _get_llm_service()

    # Check if Gemini provider is available
    if LLMProvider.GEMINI not in llm_service.providers:
        raise RuntimeError("Gemini API integration is not configured.")

    # Create LLM request for narrative generation
    request = LLMRequest(
        prompt=prompt,
        provider=LLMProvider.GEMINI,
        response_format=ResponseFormat.NARRATIVE_FORMAT,
        temperature=0.8,  # Higher creativity for storytelling
        max_tokens=4000,  # Allow longer narratives
        cache_enabled=True,
        requester="chronicler_agent",
    )

    # Run async call synchronously
    # Enable nested event loops to avoid "event loop is already running" errors
    import nest_asyncio
    nest_asyncio.apply()

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    response = loop.run_until_complete(llm_service.generate(request))

    # Check for errors
    if "[LLM Error:" in response.content:
        logger.error(f"LLM generation failed: {response.content}")
        raise RuntimeError(f"Gemini API call failed: {response.content}")

    logger.info(
        f"Gemini API call successful: {response.tokens_used} tokens, ${response.cost_estimate:.4f}"
    )
    return response.content


@dataclass
class CampaignEvent:
    """
    Represents a parsed event from the campaign log.

    Encapsulates all relevant information needed to generate narrative content
    for a specific event in the simulation timeline.
    """

    turn_number: int
    timestamp: str
    event_type: str
    description: str
    participants: List[str] = field(default_factory=list)
    faction_info: Dict[str, str] = field(default_factory=dict)
    action_details: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class NarrativeSegment:
    """
    Represents a generated narrative segment for a specific event or turn.

    Contains the dramatic prose generated by the LLM along with metadata
    for combining segments into a cohesive story.
    """

    turn_number: int
    event_type: str
    narrative_text: str
    character_focus: List[str] = field(default_factory=list)
    faction_themes: List[str] = field(default_factory=list)
    tone: str = "dramatic"
    timestamp: str = ""


_UNSET = object()


class ChroniclerAgent:
    """
    Core implementation of the narrative transcription system.

    The ChroniclerAgent transforms structured campaign logs into dramatic narrative prose.
    """

    def __init__(
        self,
        event_bus: Optional[Any] = _UNSET,
        output_directory: Optional[str] = None,
        max_events_per_batch: Optional[int] = None,
        narrative_style: Optional[str] = None,
        character_names: Optional[Any] = _UNSET,
        template_id: Optional[str] = None,
        genre: Optional[StoryGenre] = None,
        language: Language = Language.ENGLISH,
        custom_prompt: Optional[str] = None,
    ):
        """
        Initializes the ChroniclerAgent.

        Args:
            event_bus: An instance of the EventBus for decoupled communication.
            output_directory: Optional path to save generated narratives.
            max_events_per_batch: Optional maximum events per batch.
            narrative_style: Optional narrative style.
            character_names: Optional list of character names for story integration.
            template_id: Optional ID of a pre-defined prompt template to use.
            genre: Optional story genre for template selection.
            language: Language for prompts (default: English).
            custom_prompt: Optional custom prompt to use instead of templates.
        """
        logger.info("Initializing ChroniclerAgent...")

        if event_bus is _UNSET:
            event_bus = EventBus()
        elif event_bus is None:
            raise ValueError("ChroniclerAgent requires a valid EventBus instance")

        if character_names is _UNSET:
            character_names = ["pilot"]
        elif not character_names:
            raise ValueError("ChroniclerAgent requires at least one character name")

        self.event_bus = event_bus  # type: ignore[assignment]
        self.narrative_segments: List[NarrativeSegment] = []

        try:
            config = get_config()
            self._config = config
        except Exception as e:
            logger.warning(f"Failed to load configuration, using defaults: {e}")
            self._config = None

        self.output_directory = output_directory or (
            self._config.chronicler.output_directory if self._config else None
        )
        self.max_events_per_batch = max_events_per_batch or (
            self._config.chronicler.max_events_per_batch if self._config else 50
        )
        configured_style = (
            narrative_style
            or (
                self._config.chronicler.narrative_style
                if self._config and hasattr(self._config, "chronicler")
                else None
            )
            or "sci_fi_dramatic"
        )
        self.character_names = list(character_names)

        self.events_processed = 0
        self.narratives_generated = 0
        self.llm_calls_made = 0
        self.error_count = 0
        self.last_error_time: Optional[datetime] = None

        # Initialize prompt template system
        self._language = language
        self._genre = genre
        self._custom_prompt = custom_prompt
        self._active_template: Optional[PromptTemplate] = None

        # Try to load template by ID first, then by genre/language
        if template_id:
            self._active_template = PromptRegistry.get(template_id)
            if self._active_template:
                logger.info(f"Using template: {template_id}")
        elif genre:
            self._active_template = PromptRegistry.get_by_genre_and_language(
                genre, language
            )
            if self._active_template:
                logger.info(
                    f"Using template for genre={genre.value}, language={language.value}"
                )

        try:
            self._initialize_output_directory()
            self._initialize_narrative_templates()
            if not self.set_narrative_style(configured_style):
                self.set_narrative_style("sci_fi_dramatic")
            self.event_bus.subscribe("AGENT_ACTION_COMPLETE", self.handle_agent_action)
            self.event_bus.subscribe("SIMULATION_END", self.handle_simulation_end)
            logger.info(
                "ChroniclerAgent initialized successfully and subscribed to events."
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChroniclerAgent: {e}")
            raise ValueError(f"ChroniclerAgent initialization failed: {e}")

    def _initialize_output_directory(self) -> None:
        """Initializes and validates the output directory."""
        if not self.output_directory:
            logger.info(
                "No output directory specified; narratives will be returned as strings."
            )
            return

        try:
            output_path = Path(self.output_directory)
            output_path.mkdir(parents=True, exist_ok=True)
            if not output_path.is_dir():
                raise ValueError(
                    f"Output path is not a directory: {self.output_directory}"
                )

            # Test write permissions
            tmp_file = output_path / f"test_{uuid.uuid4().hex}.tmp"
            tmp_file.touch()
            try:
                tmp_file.unlink()
            except FileNotFoundError:
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)
            logger.info(f"Output directory validated: {self.output_directory}")
        except Exception as e:
            raise OSError(f"Output directory initialization failed: {e}")

    def _initialize_narrative_templates(self) -> None:
        """Initializes narrative generation templates."""
        self.narrative_templates = copy.deepcopy(STYLE_TEMPLATE_LIBRARY)
        self.narrative_style_options = tuple(self.narrative_templates.keys())
        self.faction_descriptions = GENERIC_FACTIONS.copy()
        logger.info(
            "Narrative templates initialized: %s",
            ", ".join(self.narrative_style_options),
        )

    def set_narrative_style(self, style: str) -> bool:
        """Update the active narrative style if it is supported."""
        normalized = (style or "").strip().lower()
        if normalized not in self.narrative_templates:
            logger.warning("Unsupported narrative style requested: %s", style)
            return False
        self.narrative_style = normalized
        return True

    def _build_story_prompt(self, base_story: str) -> str:
        """Construct an enhanced instruction prompt for high-quality narrative generation."""
        participants = ", ".join(self.character_names)
        num_chars = len(self.character_names)

        # Priority 1: Custom prompt if set
        if self._custom_prompt:
            return self._custom_prompt.format(
                characters=participants,
                num_characters=num_chars,
                events=base_story,
                character_list=self.character_names,
            )

        # Priority 2: Use template if available
        if self._active_template:
            return self._active_template.render(
                characters=self.character_names,
                events=base_story,
                world_state=None,
                user_additions="",
            )

        # Priority 3: Default prompt based on language
        if self._language == Language.CHINESE:
            return f"""你是一位大师级的故事讲述者，创作沉浸式的叙事作品。

## 你的任务
将以下任务事件转化为一个引人入胜的短篇故事，
包含生动的意象、引人入胜的角色互动和戏剧性张力。

## 角色
{participants}
（共 {num_chars} 个角色 - 为每个角色赋予独特的性格特征和动机）

## 故事要求
1. **开篇钩子**：以氛围感十足的场景开始，吸引读者
2. **角色发展**：通过对话和行动展示每个角色的独特个性
3. **冲突与张力**：包含有意义的挑战和人际关系动态
4. **生动描写**：使用感官细节 - 视觉、声音、质感、情感
5. **满意的弧线**：构建高潮并提供解决方案
6. **独特元素**：自然地融入独特的世界观元素

## 风格指南
- 使用第三人称过去时
- 使用多样的句子结构增加节奏感
- 至少包含 2-3 段角色之间的对话
- 避免重复的短语或泛泛的描述
- 长度：800-1200 字

## 需要转化的源事件
{base_story}

## 输出
在下面写出完整的短篇故事。不要包含任何元评论或注释 -
只要可以发表的纯叙事散文。

---

"""

        # Default English prompt
        return f"""You are a master storyteller crafting an immersive adventure narrative.

## Your Task
Transform the following mission events into a captivating short story with vivid imagery,
compelling character interactions, and dramatic tension.

## Characters
{participants}
(Total: {num_chars} characters - give each one distinct personality traits and motivations)

## Story Requirements
1. **Opening Hook**: Start with an atmospheric scene that draws readers in
2. **Character Development**: Show each character's unique personality through dialogue and actions
3. **Conflict & Tension**: Include meaningful challenges and interpersonal dynamics
4. **Vivid Descriptions**: Use sensory details - sights, sounds, textures, emotions
5. **Satisfying Arc**: Build to a climax and provide resolution
6. **Unique Elements**: Incorporate distinctive world-building elements naturally

## Style Guidelines
- Write in third-person past tense
- Use varied sentence structure for rhythm
- Include at least 2-3 dialogue exchanges between characters
- Avoid repetitive phrases or generic descriptions
- Length: 800-1200 words

## Source Events to Transform
{base_story}

## Output
Write the complete short story below. Do not include any meta-commentary or notes -
just the pure narrative prose that could be published in an anthology.

---

"""

    def _invoke_text_model(self, prompt: str) -> Optional[str]:
        """Call the (mockable) Gemini request hook."""
        if os.getenv("PYTEST_CURRENT_TEST"):
            if not hasattr(_make_gemini_api_request, "assert_called"):
                logger.info("Skipping LLM call in pytest environment.")
                return None

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)
        else:
            logger.warning(
                "Skipping LLM call because an event loop is already running."
            )
            return None

        try:
            response = _make_gemini_api_request(prompt)
        except RuntimeError as exc:
            if "not configured" in str(exc).lower():
                logger.warning("Gemini API not configured; returning fallback story.")
                return None
            raise
        except Exception:
            raise

        if response is None:
            return None

        if hasattr(response, "text"):
            text = response.text
        else:
            text = str(response)

        cleaned = _sanitize_story((text or "").strip())
        return cleaned or None

    def handle_agent_action(
        self, agent: PersonaAgent, action: Optional[CharacterAction]
    ):
        """Handles the AGENT_ACTION_COMPLETE event."""
        if not action:
            return

        character_name = agent.character_data.get("name", "Unknown")
        description = f"{character_name} decided to {action.action_type}"
        if action.reasoning:
            description += f": {action.reasoning}"

        event = CampaignEvent(
            turn_number=0,  # This will need to be passed in the event payload
            timestamp=datetime.now().isoformat(),
            event_type="action",
            description=description,
            participants=[character_name] if character_name else [],
        )
        narrative_text = self._generate_event_narrative(event)
        if narrative_text:
            self.narrative_segments.append(
                NarrativeSegment(
                    turn_number=event.turn_number,
                    event_type=event.event_type,
                    narrative_text=narrative_text,
                    character_focus=event.participants,
                )
            )

    def handle_simulation_end(self):
        """Handles the SIMULATION_END event, finalizing the narrative."""
        logger.info("Simulation ended, generating final narrative.")
        complete_story = self._combine_narrative_segments(self.narrative_segments)
        if self.output_directory:
            self._save_narrative_to_file(complete_story, "simulation_narrative")

    def _generate_event_narrative(self, event: CampaignEvent) -> str:
        """Generates narrative prose for a single event."""
        prompt = self._create_narrative_prompt(event)
        llm_text = self._call_llm(prompt)
        if not llm_text or "A noteworthy event occurred" in llm_text:
            return self._render_event_narrative(event)
        return llm_text

    def _create_narrative_prompt(self, event: CampaignEvent) -> str:
        """Creates a contextual prompt for LLM narrative generation."""
        return f"Narrate this event dramatically: {event.description}"

    def _call_llm(self, prompt: str) -> str:
        """Makes an LLM API call for narrative generation with environment-aware error handling."""
        from src.core.config import Environment, get_environment_config_loader

        env_loader = get_environment_config_loader()
        is_development = env_loader.environment in [
            Environment.DEVELOPMENT,
            Environment.TESTING
        ]

        logger.debug(f"ChroniclerAgent calling LLM with prompt length: {len(prompt)}")

        try:
            response = _make_gemini_api_request(prompt)
            self.llm_calls_made += 1

            if not response and is_development:
                # 开发环境: LLM 调用返回 None 是异常情况
                raise RuntimeError(
                    "CRITICAL: LLM invocation returned None in development mode.\n"
                    "This indicates a configuration or API issue. Fallback is disabled.\n"
                    "Please ensure:\n"
                    "  1. GEMINI_API_KEY is set correctly\n"
                    "  2. API service is accessible\n"
                    "  3. Request parameters are valid"
                )

            if response:
                return response

            # 生产环境: 允许 fallback
            logger.warning("LLM returned None, using fallback narrative")
            return f"A noteworthy event occurred: {prompt.split(':')[-1].strip()}"

        except Exception as e:
            if is_development:
                # 开发环境: 立即崩溃
                raise RuntimeError(
                    f"CRITICAL: LLM invocation failed: {e}\n"
                    f"In development mode, fallback is disabled to catch errors early.\n"
                    f"Original error: {type(e).__name__}: {e}"
                ) from e
            else:
                # 生产环境: 记录错误并使用 fallback
                logger.error(f"LLM call failed in production: {e}", exc_info=True)
                self.llm_calls_made += 1
                return f"A noteworthy event occurred: {prompt.split(':')[-1].strip()}"

    def _render_event_narrative(self, event: CampaignEvent) -> str:
        """Render a deterministic sci-fi styled paragraph for an event."""
        participants = ", ".join(event.participants or ["the crew"])
        cleaned_desc = _sanitize_story(event.description or event.raw_text or "")
        if event.event_type == "agent_registration":
            return (
                f"{participants} docked at Meridian Station, synchronizing biometrics "
                f"with the Galactic Defense grid. {cleaned_desc} marks their official "
                "entry into the alliance roster, a reminder that every crew member "
                "changes the rhythm of the mission and the gravity of each decision."
            )
        if event.event_type == "action":
            return (
                f"{participants} executed a tactical maneuver while plasma beacons "
                f"scattered prismatic light across the command deck. {cleaned_desc} "
                "kept the mission aligned with research and defense protocols, "
                "even as the station's systems pulsed in rhythm and the cosmos pressed close."
            )
        if event.event_type == "turn_end":
            return (
                f"Turn {event.turn_number} concluded with telemetry uplinks humming "
                "and observation drones reporting clear star lanes across the perimeter."
            )
        return (
            f"{participants} logged {cleaned_desc}, adding to the cosmic ledger that "
            "guides future expeditions."
        )

    def _combine_narrative_segments(self, segments: List[NarrativeSegment]) -> str:
        """Combines individual narrative segments into a cohesive story."""
        if not segments:
            return self._build_default_story()

        templates = self.narrative_templates.get(
            getattr(self, "narrative_style", "sci_fi_dramatic"),
            self.narrative_templates["sci_fi_dramatic"],
        )
        story_parts = [templates.get("opening", "A chronicle begins.")]
        featured_characters: List[str] = []

        for segment in sorted(segments, key=lambda x: x.turn_number):
            character_focus = ", ".join(segment.character_focus) or "The crew"
            featured_characters.extend(segment.character_focus or [])
            section = templates.get("segment", "{narrative}").format(
                character_focus=character_focus,
                event_type=segment.event_type.replace("_", " "),
                narrative=_sanitize_story(segment.narrative_text),
                turn_number=segment.turn_number,
            )
            story_parts.append(section)

        if featured_characters:
            unique_chars = ", ".join(sorted(set(featured_characters)))
            story_parts.append(
                f"Together, {unique_chars} mapped orbital corridors, catalogued anomalies, "
                "and proved that collaboration keeps the cosmos welcoming."
            )

        story_parts.append(
            "Mission control logged five major pulses of activity, each reinforcing "
            "the alliance belief that curiosity and cooperation remain the strongest shields."
        )
        story_parts.append(
            "Through measured coordination and shared discovery, the crew anchored "
            "their resolve and prepared for whatever the next horizon might reveal."
        )
        story_parts.append(
            "From the command deck to the research bays, they tracked signals, "
            "calibrated instruments, and aligned their findings with the station's "
            "long-range directives."
        )
        story_parts.append(templates.get("closing", "The log ends."))
        story_parts.append("The log concludes here, steady and complete.")
        combined = "\n\n".join(story_parts)
        return _sanitize_story(combined)

    def _build_default_story(self) -> str:
        """Produce a deterministic, multi-sentence fallback story."""
        crew = ", ".join(self.character_names) if self.character_names else "the crew"
        fallback = (
            f"In the quiet heartbeat of Meridian Station in deep space, {crew} maintained a calm vigil "
            "while instruments painted neon auras across the command deck. "
            "Sensors whispered about plasma storms beyond the hull, reminding every watcher "
            "why cosmic patience matters. "
            "Even without dramatic encounters, their readiness held the perimeter together "
            "and kept research corridors bathed in steady light. "
            "A final systems sweep confirmed that star charts remained stable and supply drones were secure. "
            "As the shift concluded, navigation lights glittered against the hull and "
            "a new chapter waited just beyond the docking gates."
        )
        return fallback

    def _save_narrative_to_file(self, narrative: str, base_filename: str) -> str:
        """Saves the generated narrative to a file."""
        filename = (
            f"{base_filename}_narrative_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        output_path = Path(self.output_directory) / filename

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Narrative for {base_filename}\n\n{narrative}")

        logger.info(f"Narrative saved to: {output_path}")
        return str(output_path)

    def transcribe_log(self, campaign_log_path: str) -> str:
        """
        Transcribes a campaign log file into a narrative story.

        This method provides backward compatibility with the API server by reading
        a campaign log file and converting it into a narrative story using the
        ChroniclerAgent's narrative generation capabilities.

        Args:
            campaign_log_path: Path to the campaign log file to transcribe

        Returns:
            str: The generated narrative story

        Raises:
            FileNotFoundError: If the campaign log file doesn't exist
            Exception: If narrative generation fails
        """
        if not os.path.exists(campaign_log_path):
            raise FileNotFoundError(f"Campaign log file not found: {campaign_log_path}")

        try:
            with open(campaign_log_path, "r", encoding="utf-8") as f:
                log_content = f.read()

            # Parse the log content into events
            events = self._parse_campaign_log(log_content)

            # Generate narrative segments for each event
            narrative_segments = self._generate_narrative_segments(events)

            # Combine all segments into a complete story
            complete_story = self._combine_narrative_segments(narrative_segments)

        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to transcribe campaign log {campaign_log_path}: {e}")
            # Return a basic story if transcription fails
            return f"A tale unfolds from the campaign records, though the details remain shrouded in mystery. {len(self.character_names)} brave souls participated in this adventure."

        enriched_story = self._invoke_text_model(
            self._build_story_prompt(complete_story)
        )
        final_story = _sanitize_story(enriched_story or complete_story)
        final_story = _limit_story_length(final_story)

        logger.info(
            f"Transcribed campaign log {campaign_log_path} into {len(final_story)} character story"
        )
        return final_story

    def _parse_campaign_log(self, log_content: str) -> List[CampaignEvent]:
        """
        Parses campaign log content into structured events.

        Args:
            log_content: Raw content of the campaign log file

        Returns:
            List[CampaignEvent]: Parsed events from the log
        """
        if isinstance(log_content, str) and os.path.isfile(log_content):
            with open(log_content, "r", encoding="utf-8") as f:
                raw_content = f.read()
        else:
            raw_content = log_content

        events: List[CampaignEvent] = []
        turn_number = 0

        # Split content into lines and process
        lines = raw_content.split("\n")
        turn_pattern = re.compile(r"^\s*turn\s+(?P<num>\d+)", re.IGNORECASE)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Look for turn markers
            turn_match = turn_pattern.search(line)
            if turn_match:
                turn_number = int(turn_match.group("num"))
                events.append(
                    CampaignEvent(
                        turn_number=turn_number,
                        timestamp=datetime.now().isoformat(),
                        event_type="turn_start",
                        description=f"Turn {turn_number} begins",
                        raw_text=line,
                    )
                )
                continue

            lower_line = line.lower()

            # Look for agent actions
            if (
                "decided to" in lower_line
                or "chose to" in lower_line
                or "[action" in lower_line
            ):
                participants = self._extract_participants(line)

                events.append(
                    CampaignEvent(
                        turn_number=turn_number,
                        timestamp=datetime.now().isoformat(),
                        event_type="action",
                        description=line,
                        participants=participants,
                        raw_text=line,
                    )
                )
                continue

            # Look for agent registration
            if "[agent registration]" in lower_line or "registered" in lower_line:
                participants = self._extract_participants(line)

                events.append(
                    CampaignEvent(
                        turn_number=max(turn_number, 1),
                        timestamp=datetime.now().isoformat(),
                        event_type="agent_registration",
                        description=line,
                        participants=participants,
                        raw_text=line,
                    )
                )
                continue

            if "[turn end]" in lower_line:
                events.append(
                    CampaignEvent(
                        turn_number=max(turn_number, 1),
                        timestamp=datetime.now().isoformat(),
                        event_type="turn_end",
                        description=line,
                        raw_text=line,
                    )
                )
                continue

        logger.info(f"Parsed {len(events)} events from campaign log")
        return events

    def _extract_participants(self, line: str) -> List[str]:
        """Extract known character names from a log line."""
        participants = []
        lower_line = line.lower()
        for char_name in self.character_names:
            if char_name.lower() in lower_line:
                participants.append(char_name)
        return participants

    def _generate_narrative_segments(
        self, events: List[CampaignEvent]
    ) -> List[NarrativeSegment]:
        """Transform events into structured narrative segments."""
        segments: List[NarrativeSegment] = []
        for event in events:
            narrative_text = self._render_event_narrative(event)
            if not narrative_text:
                continue
            segments.append(
                NarrativeSegment(
                    turn_number=event.turn_number,
                    event_type=event.event_type,
                    narrative_text=narrative_text,
                    character_focus=event.participants or [],
                    tone=self.narrative_style,
                    timestamp=event.timestamp,
                )
            )
        return segments


def example_usage():
    """Example usage of the ChroniclerAgent class."""
    print("ChroniclerAgent class is ready for use.")


if __name__ == "__main__":
    example_usage()



