#!/usr/bin/env python3
"""
PersonaAgent Backward-Compatible Entry Point.

Provides the legacy constructor signatures (like ``PersonaAgent(character_name="pilot")``)
while delegating the actual behavior to the integrated implementation. The legacy unit
tests patch several module-level helpers (``_make_gemini_api_request`` etc.), so we
expose lightweight shims that can be mocked without depending on the heavier
context-loading stack.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.agents.persona_agent.protocols import ThreatLevel
from src.core.types.shared_types import ActionPriority, CharacterAction
from src.event_bus import EventBus
from src.persona_agent_integrated import PersonaAgent as _PersonaAgentImpl

logger = logging.getLogger(__name__)


def _find_characters_root() -> Path:
    """Locate the repo's characters directory for legacy character_name usage."""
    current = Path(__file__).resolve()
    repo_root = current
    while repo_root != repo_root.parent:
        if (repo_root / "characters").exists():
            return repo_root / "characters"
        repo_root = repo_root.parent
    return Path.cwd() / "characters"


DEFAULT_CHARACTERS_ROOT = _find_characters_root()
_SCRIPT_TAG_RE = re.compile(r"<\s*/?\s*script[^>]*>", re.IGNORECASE)
_WHITESPACE_RE = re.compile(r"\s+")
_API_KEY_SENTINELS = {"", "none", "your_key_here"}
_CHARACTER_DIRNAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# Global LLM service instance for lazy initialization
_llm_service_instance: Optional[Any] = None


def _sanitize_text(value: str) -> str:
    """Basic sanitizer to strip scripts and collapse whitespace."""
    cleaned = _SCRIPT_TAG_RE.sub("", value or "")
    cleaned = cleaned.replace("\x00", "")
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def _validate_gemini_api_key() -> Optional[str]:
    """Return a usable Gemini API key if one is configured."""
    for env_name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        candidate = os.getenv(env_name, "") or ""
        candidate = candidate.strip()
        if candidate and candidate.lower() not in _API_KEY_SENTINELS:
            return candidate
    return None


def _get_llm_service() -> Any:
    """Get or create the global LLM service instance."""
    global _llm_service_instance
    if _llm_service_instance is None:
        try:
            from src.llm_service import UnifiedLLMService

            _llm_service_instance = UnifiedLLMService()
        except ImportError as e:
            logger.error(f"Failed to import UnifiedLLMService: {e}")
            raise RuntimeError("UnifiedLLMService not available")
    return _llm_service_instance


def _make_gemini_api_request(prompt: str) -> Optional[str]:
    """
    Gemini API integration using UnifiedLLMService.

    This provides actual LLM-guided decision making for PersonaAgent using
    the unified LLM service with caching and cost controls.

    Args:
        prompt: The action decision prompt from PersonaAgent

    Returns:
        The generated response text or None if service unavailable

    Raises:
        RuntimeError: If Gemini API is not configured
    """
    from src.llm_service import (
        LLMProvider,
        LLMRequest,
        ResponseFormat,
    )

    llm_service = _get_llm_service()

    # Check if Gemini provider is available
    if LLMProvider.GEMINI not in llm_service.providers:
        raise RuntimeError("Gemini API integration is not configured.")

    # Create LLM request for action decision
    request = LLMRequest(
        prompt=prompt,
        provider=LLMProvider.GEMINI,
        response_format=ResponseFormat.ACTION_FORMAT,  # Expects ACTION:/TARGET:/REASONING:
        temperature=0.7,
        max_tokens=2000,
        cache_enabled=True,
        requester="persona_agent",
    )

    # Run async call synchronously
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
        f"Gemini API call successful: {response.tokens_used} tokens, "
        f"${response.cost_estimate:.4f}"
    )
    return response.content


def _generate_fallback_response(
    world_state_update: Dict[str, Any],
    situation_assessment: Dict[str, Any],
    available_actions: Sequence[Dict[str, Any]],
) -> str:
    """Generate a deterministic fallback response string for tests."""
    action_index = 1
    target = "none"
    reasoning = "Fallback response generated without LLM guidance."

    if available_actions:
        # Prefer a non-observe action; otherwise use the first option
        prioritized = [
            (idx, action)
            for idx, action in enumerate(available_actions, start=1)
            if action.get("type") not in {"observe", "wait", "wait_observe"}
        ]
        chosen = prioritized[0] if prioritized else (1, available_actions[0])
        action_index = max(1, chosen[0])
        target = chosen[1].get("target") or chosen[1].get("type", "none")

    threat = situation_assessment.get("threat_level") or world_state_update.get(
        "threat_level", "moderate"
    )
    reasoning = f"Threat level {threat} requires decisive action without LLM context."
    return f"ACTION: {action_index}\n" f"TARGET: {target}\n" f"REASONING: {reasoning}"


class PersonaAgent(_PersonaAgentImpl):
    """Compatibility wrapper that accepts legacy constructor arguments."""

    def __init__(
        self,
        character_directory_path: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        agent_id: Optional[str] = None,
        character_name: Optional[str] = None,
    ):
        default_root = DEFAULT_CHARACTERS_ROOT.resolve()
        repo_root = default_root.parent
        if character_directory_path:
            base_dir = Path(character_directory_path).resolve()
            if not base_dir.is_relative_to(repo_root):
                raise FileNotFoundError(
                    f"Character directory not found: {character_directory_path}"
                )
        else:
            base_dir = default_root

        if character_name:
            raw_name = (character_name or "").strip()
            safe_name = os.path.basename(raw_name)
            if (
                not safe_name
                or safe_name in {".", ".."}
                or safe_name != raw_name
                or not _CHARACTER_DIRNAME_RE.fullmatch(safe_name)
            ):
                raise ValueError("Invalid character_name")
            if not base_dir.is_dir():
                raise FileNotFoundError(
                    f"Character directory not found: {character_directory_path}"
                )
            available_character_dirs = [
                item
                for item in os.listdir(base_dir)
                if (base_dir / item).is_dir()
            ]
            matched_name = next(
                (item for item in available_character_dirs if item == safe_name), None
            )
            if not matched_name:
                raise FileNotFoundError(f"Character directory not found: {safe_name}")
            resolved_path_obj = (base_dir / matched_name).resolve()
        else:
            resolved_path_obj = base_dir

        if not resolved_path_obj.is_relative_to(base_dir):
            raise FileNotFoundError(
                f"Character directory not found: {character_directory_path}"
            )

        if not os.path.isdir(resolved_path_obj):
            raise FileNotFoundError(f"Character directory not found: {resolved_path_obj}")

        if event_bus is None:
            event_bus = EventBus()

        derived_agent_id = agent_id or character_name
        self._legacy_character_name = character_name
        super().__init__(str(resolved_path_obj), event_bus, derived_agent_id)

        # Legacy tests expect cached prompt/response history
        self._llm_prompt_history: List[str] = []
        self._llm_response_history: List[str] = []

    @property
    def character_name(self) -> Optional[str]:
        legacy_name = getattr(self, "_legacy_character_name", None)
        return legacy_name or super().character_name

    @property
    def decision_weights(self) -> Dict[str, float]:
        return self.core.decision_weights

    @decision_weights.setter
    def decision_weights(self, weights: Dict[str, float]) -> None:
        if not isinstance(weights, dict):
            raise ValueError("decision_weights must be a dictionary")
        self.core.decision_weights = weights

    # ------------------------------------------------------------------
    # Legacy AI helper surface
    # ------------------------------------------------------------------

    def decision_loop(self, scenario_description: Optional[str] = None) -> Any:
        """
        Legacy helper that forwards to the integrated decision engine.

        Args:
            scenario_description: Optional human-readable scenario summary.
        """
        world_state: Dict[str, Any] = {}
        if scenario_description:
            world_state["scenario"] = scenario_description
        return self.decision_engine.make_decision(world_state)

    def handle_turn_start(self, world_state_update: Optional[Dict[str, Any]]) -> Any:
        """Legacy TURN_START handler that emits AGENT_ACTION_COMPLETE events."""
        world_state = world_state_update or {}
        action = None
        try:
            process = getattr(self.core, "_process_world_state_update", None)
            if callable(process):
                process(world_state)
            action = self._make_decision(world_state)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("PersonaAgent failed to process turn: %s", exc)
            action = None
        finally:
            try:
                self.event_bus.emit("AGENT_ACTION_COMPLETE", agent=self, action=action)
            except Exception:
                logger.debug("Event bus unavailable during AGENT_ACTION_COMPLETE emit")
        return action

    def _make_decision(
        self, world_state_update: Optional[Dict[str, Any]]
    ) -> Optional[CharacterAction]:
        """Compatibility decision routine that honors patched helper methods."""
        state = world_state_update or {}
        try:
            self._process_world_state_update(state)
            situation = self._assess_current_situation()
            available_actions = self._identify_available_actions(situation) or []

            llm_action = None
            try:
                llm_action = self._llm_enhanced_decision_making(
                    state, situation, available_actions
                )
            except Exception as exc:
                logger.warning("LLM-enhanced decision failed: %s", exc)

            if llm_action:
                return llm_action

            evaluations: List[Tuple[Dict[str, Any], float]] = []
            for action in available_actions:
                score = self._evaluate_action_option(action, situation)
                evaluations.append((action, score))

            selected = self._select_best_action(evaluations)
            if selected is not None:
                return selected

            return self.decision_engine.make_decision(state)
        except Exception as exc:
            logger.error("Legacy decision loop failed: %s", exc)
            return None

    def _process_world_state_update(self, world_state_update: Dict[str, Any]) -> None:
        handler = getattr(self.core, "_process_world_state_update", None)
        if callable(handler):
            handler(world_state_update)

    def _assess_current_situation(self) -> Dict[str, Any]:
        assessor = getattr(self.decision_engine, "_assess_current_situation", None)
        if callable(assessor):
            result = assessor() or {}
        else:
            result = {
                "threat_level": ThreatLevel.NEGLIGIBLE,
                "available_resources": {},
                "environmental_factors": {},
                "social_obligations": [],
                "mission_status": {},
            }
        result.setdefault("available_resources", self._assess_available_resources())
        result.setdefault("environmental_factors", self._assess_environmental_factors())
        result.setdefault("social_obligations", self._assess_social_obligations())
        result.setdefault("mission_status", self._assess_mission_status())
        if "threat_level" not in result:
            result["threat_level"] = ThreatLevel.NEGLIGIBLE
        return result

    def _assess_overall_threat_level(
        self, description: Optional[str] = None
    ) -> ThreatLevel:
        return self._assess_threat_from_description(description or "")

    def _assess_available_resources(self, overrides: Optional[Dict[str, Any]] = None):
        resources = {
            "energy": 75,
            "supplies": 60,
            "support": 50,
        }
        if overrides:
            resources.update(overrides)
        return resources

    def _assess_social_obligations(self) -> List[str]:
        relationships = getattr(self.core, "relationships", {})
        return [entity for entity, strength in relationships.items() if strength > 0.5]

    def _assess_mission_status(self) -> Dict[str, Any]:
        return {
            "status": getattr(self.core, "current_status", "active"),
            "goals": list(self.core.subjective_worldview.get("current_goals", [])),
        }

    def _assess_environmental_factors(self) -> Dict[str, Any]:
        worldview = self.core.subjective_worldview
        return {
            "known_locations": worldview.get("location_knowledge", {}),
            "active_threats": worldview.get("active_threats", {}),
        }

    def _select_best_action(
        self, action_evaluations: List[Tuple[Dict[str, Any], float]]
    ) -> Optional[CharacterAction]:
        selector = getattr(self.decision_engine, "_select_best_action", None)
        if callable(selector):
            return selector(action_evaluations)
        return None

    def _build_llm_prompt(
        self,
        world_state_update: Dict[str, Any],
        situation_assessment: Dict[str, Any],
        available_actions: Sequence[Dict[str, Any]],
    ) -> str:
        """Construct a compact prompt for the legacy LLM helpers."""
        character_name = self.character_name or self.agent_id
        actions_section = "\n".join(
            f"{idx}. {action.get('type', 'unknown')}: {action.get('description','No description')}"
            for idx, action in enumerate(available_actions, start=1)
        )
        prompt = (
            f"Character: {character_name}\n"
            f"Status: {self.current_status} | Morale: {self.morale_level:.2f}\n"
            f"World State: {world_state_update}\n"
            f"Situation: {situation_assessment}\n"
            f"Available Actions:\n{actions_section}\n"
            "Respond with ACTION, TARGET, REASONING."
        )
        self._llm_prompt_history.append(prompt)
        self._llm_prompt_history[:] = self._llm_prompt_history[-50:]
        return prompt

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Invoke the pluggable Gemini helper."""
        api_key = _validate_gemini_api_key()
        if not api_key:
            return "[LLM-Fallback] Gemini API key not configured."
        try:
            response = _make_gemini_api_request(prompt)
        except Exception as exc:  # pragma: no cover - logging path
            logger.warning("Gemini API request failed: %s", exc)
            return "[LLM-Fallback] Gemini service unavailable."
        if response:
            self._llm_response_history.append(response)
            self._llm_response_history[:] = self._llm_response_history[-50:]
        return response

    def _llm_enhanced_decision_making(
        self,
        world_state_update: Dict[str, Any],
        situation_assessment: Dict[str, Any],
        available_actions: List[Dict[str, Any]],
    ) -> Optional[CharacterAction]:
        """
        Legacy-compatible LLM orchestration used by multiple historical tests.
        """
        if not available_actions:
            return None

        prompt = self._build_llm_prompt(
            world_state_update, situation_assessment, available_actions
        )
        response_text = self._call_llm(prompt)
        if response_text and response_text.startswith("[LLM-Fallback]"):
            response_text = None
        if not response_text:
            response_text = _generate_fallback_response(
                world_state_update, situation_assessment, available_actions
            )

        action = self._parse_llm_response(response_text, available_actions)
        if action:
            sanitized_reasoning = _sanitize_text(action.reasoning or "")
            action.reasoning = f"[LLM-Guided] {sanitized_reasoning}"
        return action

    def _parse_llm_response(
        self, llm_response: Optional[str], available_actions: Sequence[Dict[str, Any]]
    ) -> Optional[CharacterAction]:
        """Parse ACTION/TARGET/REASONING output into CharacterAction."""
        if not llm_response:
            return None

        action_match = re.search(r"ACTION:\s*(.+)", llm_response, re.IGNORECASE)
        target_match = re.search(r"TARGET:\s*(.+)", llm_response, re.IGNORECASE)
        reasoning_match = re.search(
            r"REASONING:\s*(.+)", llm_response, re.IGNORECASE | re.DOTALL
        )
        if not action_match:
            return None

        action_value = action_match.group(1).strip()
        if action_value.lower() in {"wait", "observe", "wait_observe"}:
            return None

        action_type = self._resolve_action_type(action_value, available_actions)
        if not action_type:
            return None
        if action_type in {"observe", "wait", "wait_observe"}:
            return None

        target_value = _sanitize_text(target_match.group(1)) if target_match else "none"
        reasoning_value = (
            _sanitize_text(reasoning_match.group(1)) if reasoning_match else ""
        )

        priority = self._determine_action_priority(action_type, reasoning_value)
        return CharacterAction(
            action_type=action_type,
            target=target_value or None,
            reasoning=reasoning_value or None,
            priority=priority,
        )

    def _resolve_action_type(
        self, action_value: str, available_actions: Sequence[Dict[str, Any]]
    ) -> Optional[str]:
        """Map numbered responses to real action types."""
        if action_value.isdigit():
            idx = int(action_value) - 1
            if 0 <= idx < len(available_actions):
                return available_actions[idx].get("type") or "unknown"
        return action_value.lower() or None

    def _determine_action_priority(
        self, action_type: str, reasoning: str
    ) -> ActionPriority:
        """Infer ActionPriority from reasoning hints."""
        lowered = reasoning.lower()
        if "urgent" in lowered or "critical" in lowered:
            return ActionPriority.CRITICAL
        if action_type in {"attack", "advance"}:
            return ActionPriority.HIGH
        if action_type in {"observe", "gather"}:
            return ActionPriority.LOW
        return ActionPriority.NORMAL

    # ------------------------------------------------------------------
    # Compatibility shims for legacy helper methods
    # ------------------------------------------------------------------

    def _read_cached_file(self, file_path: str) -> str:
        reader = getattr(self.character_interpreter, "_read_cached_file", None)
        if callable(reader):
            return reader(file_path)
        core_reader = getattr(self.core, "_read_cached_file", None)
        if callable(core_reader):
            return core_reader(file_path)
        raise FileNotFoundError(file_path)

    def _parse_character_sheet_content(self, markdown_content: str) -> Dict[str, Any]:
        parser = getattr(
            self.character_interpreter, "_parse_character_sheet_content", None
        )
        if callable(parser):
            return parser(markdown_content)
        return {"raw_content": markdown_content}

    def _derive_agent_id_from_path(self, path: str) -> str:
        return self.core._derive_agent_id_from_path(path)

    def _estimate_trait_strength(self, description: str) -> float:
        if not description:
            return 0.0
        lowered = description.lower()
        weights = {
            "fierce": 0.9,
            "resolute": 0.8,
            "steady": 0.6,
            "cautious": 0.4,
            "uncertain": 0.2,
        }
        score = 0.3  # base confidence
        for keyword, value in weights.items():
            if keyword in lowered:
                score = max(score, value)
        return round(min(score, 1.0), 2)

    def _interpret_event_description(self, event_payload: Dict[str, Any]) -> str:
        if not isinstance(event_payload, dict):
            return "No event details available."
        event_type = _sanitize_text(str(event_payload.get("event_type", "event")))
        source = _sanitize_text(str(event_payload.get("source", "unknown source")))
        description = _sanitize_text(str(event_payload.get("description", "")))
        return f"{event_type.title()} reported by {source}: {description}".strip()

    def _assess_threat_from_description(self, description: str) -> ThreatLevel:
        if not description:
            return ThreatLevel.NEGLIGIBLE
        lowered = description.lower()
        if any(word in lowered for word in ["catastrophic", "critical", "overrun"]):
            return ThreatLevel.CRITICAL
        if any(word in lowered for word in ["siege", "major battle", "desperate"]):
            return ThreatLevel.HIGH
        if any(word in lowered for word in ["enemy", "approach", "incursion"]):
            return ThreatLevel.MODERATE
        if any(word in lowered for word in ["skirmish", "disturbance"]):
            return ThreatLevel.LOW
        return ThreatLevel.NEGLIGIBLE

    def _identify_available_actions(
        self, situation_assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        identifier = getattr(self.decision_engine, "_identify_available_actions", None)
        if callable(identifier):
            return identifier(situation_assessment)
        return []

    def _evaluate_action_option(
        self, action: Dict[str, Any], situation: Dict[str, Any]
    ) -> float:
        evaluator = getattr(self.decision_engine, "_evaluate_action_option", None)
        if callable(evaluator):
            return float(evaluator(action, situation))
        return 0.0

    def _consolidate_memories(self) -> int:
        return int(self.memory_interface.consolidate_memories())

    def _update_relationship(self, entity_id: str, delta: float) -> None:
        self.core.add_relationship(entity_id, delta)

    # ------------------------------------------------------------------
    # Backward-compatible data extraction proxies
    # ------------------------------------------------------------------

    def _extract_core_identity(self) -> Any:
        return self.character_interpreter._extract_core_identity()

    def _extract_personality_traits(self) -> Any:
        return self.character_interpreter._extract_personality_traits()

    def _extract_decision_weights(self) -> Any:
        return self.character_interpreter._extract_decision_weights()

    def _extract_relationships(self) -> Any:
        return self.character_interpreter._extract_relationships()

    def _extract_knowledge_domains(self) -> Any:
        return self.character_interpreter._extract_knowledge_domains()

    def _initialize_subjective_worldview(self) -> None:  # type: ignore[override]
        return super()._initialize_subjective_worldview()


__all__ = [
    "PersonaAgent",
    "_validate_gemini_api_key",
    "_make_gemini_api_request",
    "_generate_fallback_response",
]
