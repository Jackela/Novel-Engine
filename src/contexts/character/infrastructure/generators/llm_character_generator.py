from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

from src.api.schemas import CharacterGenerationResponse
from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
    CharacterGenerationResult,
    CharacterGeneratorPort,
)


class LLMCharacterGenerator(CharacterGeneratorPort):
    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        prompt_path: Path | None = None,
    ) -> None:
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._temperature = temperature
        self._prompt_path = prompt_path or (
            Path(__file__).resolve().parents[1] / "prompts" / "character_gen.yaml"
        )

    def generate(self, request: CharacterGenerationInput) -> CharacterGenerationResult:
        system_prompt = self._load_system_prompt()
        messages = self._build_messages(system_prompt, request)
        try:
            response_text = self._call_llm(messages)
            response = self._parse_response(response_text)
        except Exception as exc:  # pragma: no cover - defensive fallback
            return self._error_result(request, str(exc))
        return CharacterGenerationResult(
            name=response.name,
            tagline=response.tagline,
            bio=response.bio,
            visual_prompt=response.visual_prompt,
            traits=list(response.traits),
        )

    def _load_system_prompt(self) -> str:
        with self._prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in character_gen.yaml")
        return prompt

    def _build_messages(
        self, system_prompt: str, request: CharacterGenerationInput
    ) -> List[Dict[str, str]]:
        tone = request.tone.strip() if request.tone else "unspecified"
        user_prompt = (
            "Generate a character card with these inputs:\n"
            f"Archetype: {request.archetype}\n"
            f"Concept: {request.concept}\n"
            f"Tone: {tone}\n"
            "Return JSON only."
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - environment specific
            raise RuntimeError("openai package is required for LLM generation") from exc

        client = OpenAI()
        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
        )
        return response.choices[0].message.content or ""

    def _parse_response(self, content: str) -> CharacterGenerationResponse:
        payload = self._extract_json(content)
        return CharacterGenerationResponse.model_validate(payload)

    def _extract_json(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise

    def _error_result(
        self, request: CharacterGenerationInput, reason: str
    ) -> CharacterGenerationResult:
        return CharacterGenerationResult(
            name="Generation Error",
            tagline="Unable to generate character",
            bio=(
                "The LLM response could not be parsed into the expected schema. "
                f"Reason: {reason}"
            ),
            visual_prompt="error state, glitch textures",
            traits=["error"],
        )
