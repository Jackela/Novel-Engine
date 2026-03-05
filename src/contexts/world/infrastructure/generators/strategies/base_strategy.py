"""Base strategy for world generation."""

from abc import ABC, abstractmethod
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


class WorldGenerationStrategy(ABC):
    """Abstract base class for world generation strategies."""

    def __init__(self, generator: Any) -> None:
        """Initialize with reference to parent generator.

        Args:
            generator: The parent LLMWorldGenerator instance
        """
        self.generator = generator
        self.logger = logger.bind(strategy=self.__class__.__name__)

    @abstractmethod
    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the strategy.

        Returns:
            Strategy-specific result
        """
        pass

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        """Helper to call Gemini API via parent generator."""
        import asyncio

        return asyncio.run(self.generator._call_gemini(system_prompt, user_prompt))

    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Helper to extract JSON from response."""
        return self.generator._extract_json(content)

    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt from YAML file."""
        from pathlib import Path

        import yaml

        prompt_path = (
            Path(__file__).resolve().parents[2] / "prompts" / f"{prompt_name}.yaml"
        )
        with prompt_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        prompt = str(payload.get("system_prompt", "")).strip()
        if not prompt:
            raise ValueError(f"Missing system_prompt in {prompt_name}.yaml")
        return prompt


__all__ = ["WorldGenerationStrategy"]
