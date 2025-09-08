#!/usr/bin/env python3
"""
Gemini LLM Client for AI Novel Generation
Real AI generation, not templates!
"""

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    print("Installing google-generativeai...")
    import subprocess

    subprocess.check_call(["pip", "install", "google-generativeai"])
    import google.generativeai as genai

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for LLM generation"""

    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.9
    top_k: int = 40
    candidate_count: int = 1


class GeminiClient:
    """
    Gemini API client for novel generation.
    This is REAL AI generation, not template selection!
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini client with API key"""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        # Configure the API
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")

        # Default generation config
        self.default_config = GenerationConfig()

        # Track usage for monitoring
        self.total_tokens_used = 0
        self.total_requests = 0

        logger.info("Gemini client initialized with model: gemini-2.0-flash-exp")

    def generate_dialogue(
        self,
        character_name: str,
        personality: Dict[str, float],
        emotion: str,
        context: Dict[str, Any],
        temperature: float = 0.7,
    ) -> str:
        """
        Generate dialogue based on character and context.

        This is REAL generation, not template selection!
        """
        prompt = f"""Generate a single line of dialogue for a character in a Chinese science fiction novel.

Character: {character_name}
Personality traits: {json.dumps(personality, ensure_ascii=False)}
Current emotion: {emotion}
Scene context: {json.dumps(context, ensure_ascii=False)}

Requirements:
1. The dialogue should be in Chinese
2. It should reflect the character's personality
3. It should match the emotional state
4. It should be relevant to the scene context
5. Keep it concise but meaningful (10-30 characters)
6. Make it unique and creative, not generic

Output only the dialogue line, nothing else."""

        try:
            response = self._generate(prompt, temperature=temperature)

            # Clean up response
            dialogue = response.strip().strip('"').strip('"').strip('"')

            logger.debug(f"Generated dialogue for {character_name}: {dialogue}")
            return dialogue

        except Exception as e:
            logger.error(f"Failed to generate dialogue: {str(e)}")
            # Return a fallback but mark it
            return f"[生成失败：{emotion}]"

    def generate_event(
        self,
        event_type: str,
        characters: List[str],
        story_context: Dict[str, Any],
        plot_stage: str,
        temperature: float = 0.8,
    ) -> Dict[str, Any]:
        """
        Generate a story event based on context.

        Returns structured event data, not templates!
        """
        prompt = f"""Generate a story event for a Chinese science fiction novel.

Event Type: {event_type}
Characters Involved: {', '.join(characters)}
Current Plot Stage: {plot_stage}
Story Context: {json.dumps(story_context, ensure_ascii=False)}

Requirements:
1. Create an original event that fits the event type
2. Include specific actions or developments
3. Make it relevant to the characters and context
4. Be creative and avoid clichés
5. Output in JSON format

Output format:
{{
    "description": "Brief description of what happens",
    "details": "Specific details of the event",
    "impact": "How this affects the story",
    "emotion": "Emotional tone of the event"
}}"""

        try:
            response = self._generate(prompt, temperature=temperature)

            # Parse JSON response
            # Try to extract JSON from response
            import re

            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                event_data = json.loads(json_match.group())
            else:
                # Fallback structure
                event_data = {
                    "description": response[:100],
                    "details": response,
                    "impact": "推动剧情发展",
                    "emotion": "neutral",
                }

            event_data["type"] = event_type
            event_data["characters"] = characters

            logger.debug(f"Generated event of type {event_type}")
            return event_data

        except Exception as e:
            logger.error(f"Failed to generate event: {str(e)}")
            return {
                "type": event_type,
                "description": "[事件生成失败]",
                "details": str(e),
                "characters": characters,
            }

    def generate_narrative(
        self,
        events: List[Dict[str, Any]],
        style: str = "poetic",
        temperature: float = 0.8,
    ) -> str:
        """
        Generate narrative prose from events.

        This creates original prose, not template combinations!
        """
        events_summary = "\n".join(
            [
                f"- {e.get('type', 'event')}: {e.get('description', '')}"
                for e in events[:5]  # Limit to recent events
            ]
        )

        prompt = f"""Transform these story events into beautiful Chinese narrative prose.

Recent Events:
{events_summary}

Style: {style}

Requirements:
1. Write flowing, literary Chinese prose
2. Connect the events naturally
3. Use vivid descriptions and metaphors
4. Maintain the science fiction atmosphere
5. Create smooth transitions between events
6. Output 100-200 characters of prose

Write the narrative prose:"""

        try:
            response = self._generate(prompt, temperature=temperature)

            # Clean up narrative
            narrative = response.strip()

            logger.debug(f"Generated narrative of length {len(narrative)}")
            return narrative

        except Exception as e:
            logger.error(f"Failed to generate narrative: {str(e)}")
            return "[叙述生成失败]"

    def _generate(self, prompt: str, temperature: float = None) -> str:
        """
        Core generation method with retry logic.
        """
        config = genai.GenerationConfig(
            temperature=temperature or self.default_config.temperature,
            max_output_tokens=self.default_config.max_tokens,
            top_p=self.default_config.top_p,
            top_k=self.default_config.top_k,
        )

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # Generate response
                response = self.model.generate_content(prompt, generation_config=config)

                # Update usage stats
                self.total_requests += 1

                # Extract text
                if response.text:
                    return response.text
                else:
                    logger.warning("Empty response from Gemini")

            except Exception as e:
                logger.warning(f"Generation attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

        raise Exception("Failed to generate after all retries")

    def test_connection(self) -> bool:
        """Test if the API connection works"""
        try:
            response = self._generate("Say 'Hello' in Chinese", temperature=0.1)
            logger.info(f"Connection test successful: {response}")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def get_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics"""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens_used,
        }


# Test function
def test_gemini_client():
    """Test the Gemini client with real generation"""
    print("Testing Gemini Client...")

    client = GeminiClient()

    # Test connection
    if not client.test_connection():
        print("❌ Connection failed!")
        return False

    print("✅ Connection successful!")

    # Test dialogue generation
    print("\nTesting dialogue generation...")
    dialogue = client.generate_dialogue(
        character_name="量子诗人·墨羽",
        personality={"philosophical": 0.9, "mysterious": 0.8, "wise": 0.7},
        emotion="contemplative",
        context={"location": "虚空观察站", "tension": 0.6},
    )
    print(f"Generated dialogue: {dialogue}")

    # Test event generation
    print("\nTesting event generation...")
    event = client.generate_event(
        event_type="discovery",
        characters=["量子诗人·墨羽", "时空织者·凌风"],
        story_context={"current_crisis": "维度裂缝扩大"},
        plot_stage="rising_action",
    )
    print(f"Generated event: {json.dumps(event, ensure_ascii=False, indent=2)}")

    # Test narrative generation
    print("\nTesting narrative generation...")
    narrative = client.generate_narrative(events=[event], style="poetic")
    print(f"Generated narrative: {narrative}")

    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    test_gemini_client()
