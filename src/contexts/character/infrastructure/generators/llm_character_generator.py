from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import requests
import yaml

from src.api.schemas import CharacterGenerationResponse
from src.contexts.character.application.services.generation_service import (
    CharacterGenerationInput,
    CharacterGenerationResult,
    CharacterGeneratorPort,
)


class LLMCharacterGenerator(CharacterGeneratorPort):
    """Character generator using Gemini API."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        prompt_path: Path | None = None,
    ) -> None:
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._temperature = temperature
        self._prompt_path = prompt_path or (
            Path(__file__).resolve().parents[1] / "prompts" / "character_gen.yaml"
        )
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._base_url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self._model}:generateContent"
        )

    def generate(self, request: CharacterGenerationInput) -> CharacterGenerationResult:
        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(request)
        try:
            response_text = self._call_gemini(system_prompt, user_prompt)
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

    def _build_user_prompt(self, request: CharacterGenerationInput) -> str:
        tone = request.tone.strip() if request.tone else "unspecified"
        return (
            "Generate a character card with these inputs:\n"
            f"Archetype: {request.archetype}\n"
            f"Concept: {request.concept}\n"
            f"Tone: {tone}\n"
            "Return JSON only."
        )

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini API to generate character."""
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set")

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        # Combine system and user prompts for Gemini
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
            timeout=30,
        )

        if response.status_code == 401:
            raise RuntimeError(
                "Gemini API authentication failed - check GEMINI_API_KEY"
            )
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

    def _parse_response(self, content: str) -> CharacterGenerationResponse:
        payload = self._extract_json(content)
        return CharacterGenerationResponse.model_validate(payload)

    def _extract_json(self, content: str) -> Dict[str, Any]:
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
