"""LLM-based scene generator using Gemini API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import requests
import yaml

from src.api.schemas import SceneGenerationResponse
from src.contexts.story.application.ports.scene_generator_port import (
    SceneGenerationInput,
    SceneGenerationResult,
    SceneGeneratorPort,
)


class LLMSceneGenerator(SceneGeneratorPort):
    """Scene generator using Gemini API."""

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.8,
        prompt_path: Path | None = None,
    ) -> None:
        """Initialize the LLM scene generator."""
        self._model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self._temperature = temperature
        self._prompt_path = prompt_path or (
            Path(__file__).resolve().parents[1] / "prompts" / "scene_gen.yaml"
        )
        self._api_key = os.getenv("GEMINI_API_KEY", "")
        self._base_url = (
            f"https://generativelanguage.googleapis.com/v1/models/"
            f"{self._model}:generateContent"
        )

    def generate(self, request: SceneGenerationInput) -> SceneGenerationResult:
        """Generate a scene using the Gemini API."""
        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(request)
        try:
            response_text = self._call_gemini(system_prompt, user_prompt)
            response = self._parse_response(response_text)
        except Exception as exc:  # pragma: no cover - defensive fallback
            return self._error_result(request, str(exc))
        return SceneGenerationResult(
            title=response.title,
            content=response.content,
            summary=response.summary,
            visual_prompt=response.visual_prompt,
        )

    def _load_system_prompt(self) -> str:
        """Load the system prompt from YAML file."""
        with self._prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError("Missing system_prompt in scene_gen.yaml")
        return prompt

    def _build_user_prompt(self, request: SceneGenerationInput) -> str:
        """Build the user prompt from the request."""
        char = request.character_context
        tone = request.tone.strip() if request.tone else "unspecified"

        # Serialize character context to JSON for the prompt
        character_json = json.dumps(
            {
                "name": char.name,
                "tagline": char.tagline,
                "bio": char.bio,
                "visual_prompt": char.visual_prompt,
                "traits": char.traits,
            },
            indent=2,
        )

        return (
            f"Generate a scene with these parameters:\n\n"
            f"CHARACTER CONTEXT:\n{character_json}\n\n"
            f"SCENE TYPE: {request.scene_type}\n"
            f"TONE: {tone}\n\n"
            f"Return valid JSON only with keys: title, content, summary, visual_prompt"
        )

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Call Gemini API to generate scene."""
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
                "maxOutputTokens": 4000,
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

    def _parse_response(self, content: str) -> SceneGenerationResponse:
        """Parse the LLM response into a SceneGenerationResponse."""
        payload = self._extract_json(content)
        return SceneGenerationResponse.model_validate(payload)

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Extract JSON from the response content."""
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
        self, request: SceneGenerationInput, reason: str
    ) -> SceneGenerationResult:
        """Return an error result when generation fails."""
        return SceneGenerationResult(
            title="Generation Error",
            content=(
                f"Unable to generate scene for {request.character_context.name}. "
                f"Please try again."
            ),
            summary=f"Error: {reason[:100]}..." if len(reason) > 100 else f"Error: {reason}",
            visual_prompt="error state, glitch textures, static",
        )
