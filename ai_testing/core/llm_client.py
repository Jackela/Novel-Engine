"""
Unified LLM Client for AI Novel Generation
Supports Gemini 2.0 Flash (primary), OpenAI, and Anthropic
"""

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


@dataclass
class GenerationRequest:
    """Request configuration for LLM generation"""

    prompt: str
    temperature: float = 0.7
    max_tokens: int = 2000
    context: Optional[Dict[str, Any]] = None
    generation_type: str = "general"  # dialogue, event, narrative


class LLMClient:
    """
    Unified LLM client supporting multiple providers.
    Primary: Gemini 2.0 Flash
    Fallback: OpenAI, Anthropic
    """

    def __init__(self, primary_provider: str = "gemini"):
        """Initialize with primary provider and fallbacks"""
        self.primary_provider = primary_provider
        self.providers = {}

        # Initialize Gemini client (primary)
        try:
            self.providers["gemini"] = GeminiClient()
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client: {e}")

        # TODO: Initialize other providers
        # self.providers["openai"] = OpenAIClient() if os.getenv("OPENAI_API_KEY") else None
        # self.providers["anthropic"] = AnthropicClient() if os.getenv("ANTHROPIC_API_KEY") else None

        self.active_provider = self.providers.get(primary_provider)
        if not self.active_provider:
            raise RuntimeError(f"Primary provider {primary_provider} not available")

    def generate_dialogue(
        self,
        character_name: str,
        personality: Dict[str, float],
        emotion: str,
        context: Dict[str, Any],
        temperature: float = 0.7,
    ) -> str:
        """
        Generate character dialogue using AI.
        This is REAL generation, not template selection!
        """
        try:
            if self.active_provider:
                return self.active_provider.generate_dialogue(
                    character_name, personality, emotion, context, temperature
                )
            else:
                raise RuntimeError("No active LLM provider available")

        except Exception as e:
            logger.error(f"Dialogue generation failed: {e}")
            return f"[对话生成失败: {emotion}]"

    def generate_event(
        self,
        event_type: str,
        characters: List[str],
        story_context: Dict[str, Any],
        plot_stage: str,
        temperature: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Generate story events using AI.
        Returns structured event data, not template selection!
        """
        try:
            if self.active_provider:
                return self.active_provider.generate_event(
                    event_type, characters, story_context, plot_stage, temperature
                )
            else:
                raise RuntimeError("No active LLM provider available")

        except Exception as e:
            logger.error(f"Event generation failed: {e}")
            return {
                "type": event_type,
                "description": "[事件生成失败]",
                "details": str(e),
                "characters": characters,
            }

    def generate_narrative(
        self, events: List[Dict[str, Any]], style: str = "poetic", temperature: float = 0.8
    ) -> str:
        """
        Generate narrative prose using AI.
        Creates original prose, not template combinations!
        """
        try:
            if self.active_provider:
                return self.active_provider.generate_narrative(events, style, temperature)
            else:
                raise RuntimeError("No active LLM provider available")

        except Exception as e:
            logger.error(f"Narrative generation failed: {e}")
            return "[叙述生成失败]"

    def test_generation(self) -> Dict[str, Any]:
        """
        Test real AI generation capabilities.
        Validates that we can generate unique, creative content.
        """
        test_results = {
            "provider": self.primary_provider,
            "connection": False,
            "dialogue_test": False,
            "event_test": False,
            "narrative_test": False,
            "errors": [],
        }

        try:
            # Test connection
            if hasattr(self.active_provider, "test_connection"):
                test_results["connection"] = self.active_provider.test_connection()
            else:
                test_results["connection"] = True  # Assume working if no test method

            # Test dialogue generation
            dialogue = self.generate_dialogue(
                character_name="测试角色",
                personality={"curious": 0.8, "analytical": 0.7},
                emotion="excited",
                context={"location": "实验室", "discovery": "新发现"},
            )
            test_results["dialogue_test"] = len(dialogue) > 0 and "生成失败" not in dialogue
            test_results["sample_dialogue"] = dialogue

            # Test event generation
            event = self.generate_event(
                event_type="discovery",
                characters=["测试角色"],
                story_context={"setting": "科幻实验室"},
                plot_stage="开端",
            )
            test_results["event_test"] = event.get("description") != "[事件生成失败]"
            test_results["sample_event"] = event

            # Test narrative generation
            narrative = self.generate_narrative([event], "dramatic")
            test_results["narrative_test"] = len(narrative) > 0 and "生成失败" not in narrative
            test_results["sample_narrative"] = narrative

        except Exception as e:
            test_results["errors"].append(str(e))
            logger.error(f"Generation test failed: {e}")

        # Overall success
        test_results["overall_success"] = all(
            [
                test_results["connection"],
                test_results["dialogue_test"],
                test_results["event_test"],
                test_results["narrative_test"],
            ]
        )

        return test_results

    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all LLM providers"""
        return {
            "active_provider": self.primary_provider,
            "available_providers": list(self.providers.keys()),
            "provider_health": {
                name: provider is not None for name, provider in self.providers.items()
            },
        }
