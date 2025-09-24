"""
Response Generator
==================

Advanced response generation system for PersonaAgent fallback and enhancement.
Provides rule-based responses when LLM is unavailable and response augmentation.
"""

import logging
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from ..protocols import ThreatLevel

# Import shared types
try:
    from shared_types import ActionPriority, CharacterAction
except ImportError:
    CharacterAction = Dict
    ActionPriority = str


class ResponseCategory(Enum):
    """Categories of responses that can be generated."""

    COMBAT = "combat"
    SOCIAL = "social"
    EXPLORATION = "exploration"
    SURVIVAL = "survival"
    DIPLOMATIC = "diplomatic"
    EMOTIONAL = "emotional"
    INFORMATIONAL = "informational"
    TACTICAL = "tactical"


class ResponseTone(Enum):
    """Tone modifiers for responses."""

    FORMAL = "formal"
    CASUAL = "casual"
    AGGRESSIVE = "aggressive"
    DIPLOMATIC = "diplomatic"
    CAUTIOUS = "cautious"
    CONFIDENT = "confident"
    EMOTIONAL = "emotional"
    ANALYTICAL = "analytical"


@dataclass
class ResponseTemplate:
    """Template for generating responses."""

    category: ResponseCategory
    tone: ResponseTone
    templates: List[str]
    # personality_trait -> weight influence
    personality_weights: Dict[str, float]
    faction_weights: Dict[str, float]  # faction_belief -> weight influence
    context_requirements: List[str]  # required context keys

    def matches_context(
        self,
        personality: Dict[str, float],
        faction_beliefs: Dict[str, float],
        context: Dict[str, Any],
    ) -> float:
        """Calculate how well this template matches the current context."""
        score = 0.5  # Base score

        # Check personality alignment
        for trait, weight in self.personality_weights.items():
            if trait in personality:
                trait_value = personality[trait]
                if weight > 0 and trait_value > 0.6:
                    score += 0.2
                elif weight < 0 and trait_value < 0.4:
                    score += 0.2

        # Check faction alignment
        for belief, weight in self.faction_weights.items():
            if belief in faction_beliefs:
                belief_strength = faction_beliefs[belief]
                if weight > 0 and belief_strength > 0.6:
                    score += 0.15
                elif weight < 0 and belief_strength < 0.4:
                    score += 0.15

        # Check context requirements
        met_requirements = sum(
            1 for req in self.context_requirements if req in context
        )
        if self.context_requirements:
            score += (met_requirements / len(self.context_requirements)) * 0.2

        return max(0.0, min(1.0, score))


class ResponseGenerator:
    """
    Advanced response generation system for PersonaAgent.

    Responsibilities:
    - Generate fallback responses when LLM is unavailable
    - Provide response templates based on character traits
    - Enhance responses with personality-appropriate language
    - Generate context-appropriate dialogue and narration
    - Support multiple response categories and tones
    - Adapt responses to character emotional state
    """

    def __init__(
        self, character_id: str, logger: Optional[logging.Logger] = None
    ):
        self.character_id = character_id
        self.logger = logger or logging.getLogger(__name__)

        # Response templates and patterns
        self._templates: Dict[ResponseCategory, List[ResponseTemplate]] = {}
        self._initialize_response_templates()

        # Character-specific data
        self._personality: Dict[str, float] = {}
        self._faction_beliefs: Dict[str, float] = {}
        self._current_emotional_state: str = "neutral"

        # Generation statistics
        self._stats = {
            "total_generated": 0,
            "by_category": {cat.value: 0 for cat in ResponseCategory},
            "by_tone": {tone.value: 0 for tone in ResponseTone},
            "fallback_used": 0,
            "template_used": 0,
        }

        # Configuration
        self._config = {
            "max_response_length": 200,
            "min_response_length": 10,
            "personality_influence": 0.7,
            "emotion_influence": 0.5,
            "randomization": 0.3,
            "template_selection_threshold": 0.6,
        }

        # Vocabulary and phrase libraries
        self._vocabulary = self._initialize_vocabulary()
        self._phrase_libraries = self._initialize_phrase_libraries()

    async def generate_response(
        self,
        context: Dict[str, Any],
        category: Optional[ResponseCategory] = None,
        tone: Optional[ResponseTone] = None,
    ) -> str:
        """
        Generate response based on context and character traits.

        Args:
            context: Context information for response generation
            category: Optional specific category to use
            tone: Optional specific tone to use

        Returns:
            str: Generated character response
        """
        try:
            self.logger.debug(
                f"Generating response for category: {category}, tone: {tone}"
            )

            # Update character data from context
            await self._update_character_data(context)

            # Determine response category if not specified
            if not category:
                category = await self._determine_response_category(context)

            # Determine response tone if not specified
            if not tone:
                tone = await self._determine_response_tone(context, category)

            # Find matching templates
            matching_templates = await self._find_matching_templates(
                category, tone, context
            )

            # Generate base response
            if matching_templates:
                base_response = await self._generate_from_template(
                    matching_templates[0], context
                )
                self._stats["template_used"] += 1
            else:
                base_response = await self._generate_fallback_response(
                    category, tone, context
                )
                self._stats["fallback_used"] += 1

            # Enhance response with character traits
            enhanced_response = await self._enhance_with_personality(
                base_response, context
            )

            # Apply emotional modifiers
            emotional_response = await self._apply_emotional_modifiers(
                enhanced_response, context
            )

            # Final formatting and validation
            final_response = await self._format_and_validate(
                emotional_response
            )

            # Update statistics
            self._stats["total_generated"] += 1
            self._stats["by_category"][category.value] += 1
            self._stats["by_tone"][tone.value] += 1

            self.logger.debug(f"Generated response: {final_response[:50]}...")
            return final_response

        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return await self._get_emergency_response()

    async def generate_dialogue(
        self,
        speaker_context: Dict[str, Any],
        conversation_context: Dict[str, Any],
    ) -> str:
        """
        Generate dialogue response for conversations.

        Args:
            speaker_context: Context about the speaking character
            conversation_context: Context about the conversation

        Returns:
            str: Generated dialogue
        """
        try:
            # Determine dialogue type
            dialogue_type = conversation_context.get(
                "dialogue_type", "general"
            )

            # Select appropriate category
            category_mapping = {
                "negotiation": ResponseCategory.DIPLOMATIC,
                "combat_taunt": ResponseCategory.COMBAT,
                "social_chat": ResponseCategory.SOCIAL,
                "information_exchange": ResponseCategory.INFORMATIONAL,
                "emotional_expression": ResponseCategory.EMOTIONAL,
            }

            category = category_mapping.get(
                dialogue_type, ResponseCategory.SOCIAL
            )

            # Generate with dialogue-specific context
            context = {
                **speaker_context,
                **conversation_context,
                "is_dialogue": True,
            }

            dialogue = await self.generate_response(
                context, category, ResponseTone.CASUAL
            )

            # Format as dialogue if not already quoted
            if not (dialogue.startswith('"') and dialogue.endswith('"')):
                dialogue = f'"{dialogue}"'

            return dialogue

        except Exception as e:
            self.logger.error(f"Dialogue generation failed: {e}")
            return '"I\'m not sure what to say."'

    async def generate_action_narration(
        self, action: CharacterAction, context: Dict[str, Any]
    ) -> str:
        """
        Generate narrative description for character actions.

        Args:
            action: Action being performed
            context: Context information

        Returns:
            str: Generated action narration
        """
        try:
            action_type = action.get("action_type", "unknown")

            # Action-specific narration templates
            narration_templates = {
                "attack": [
                    "launches an aggressive strike",
                    "moves in for the attack",
                    "strikes with determined force",
                ],
                "defend": [
                    "raises defenses",
                    "takes a defensive stance",
                    "prepares to block incoming threats",
                ],
                "move": [
                    "moves carefully through the area",
                    "advances with purpose",
                    "repositions strategically",
                ],
                "communicate": [
                    "speaks with conviction",
                    "addresses the situation directly",
                    "shares their thoughts clearly",
                ],
                "explore": [
                    "investigates the surroundings",
                    "searches the area methodically",
                    "examines the environment carefully",
                ],
                "wait": [
                    "watches and waits",
                    "remains alert and ready",
                    "pauses to assess the situation",
                ],
            }

            # Get character name
            character_name = context.get("basic_info", {}).get(
                "name", "The character"
            )

            # Select appropriate template
            templates = narration_templates.get(action_type, ["takes action"])
            base_narration = random.choice(templates)

            # Add character-specific flavor
            personality = context.get("personality", {})

            # Modify based on personality
            if personality.get("aggression", 0.5) > 0.7 and action_type in [
                "attack",
                "defend",
            ]:
                modifiers = [
                    "with fierce determination",
                    "aggressively",
                    "without hesitation",
                ]
                base_narration += f" {random.choice(modifiers)}"
            elif personality.get("intelligence", 0.5) > 0.7:
                modifiers = [
                    "strategically",
                    "with careful consideration",
                    "tactically",
                ]
                base_narration += f" {random.choice(modifiers)}"

            # Format with character name
            narration = f"{character_name} {base_narration}."

            return narration

        except Exception as e:
            self.logger.error(f"Action narration generation failed: {e}")
            return f"{context.get('basic_info', {}).get('name', 'The character')} takes action."

    async def generate_emotional_response(
        self, emotion: str, intensity: float, context: Dict[str, Any]
    ) -> str:
        """
        Generate emotional response based on emotion and intensity.

        Args:
            emotion: Type of emotion (angry, happy, sad, etc.)
            intensity: Intensity of emotion (0.0 to 1.0)
            context: Context information

        Returns:
            str: Generated emotional response
        """
        try:
            # Emotional response templates
            emotion_templates = {
                "angry": {
                    "low": ["shows mild irritation", "seems somewhat annoyed"],
                    "medium": [
                        "displays clear anger",
                        "shows growing frustration",
                    ],
                    "high": ["erupts in fury", "blazes with intense anger"],
                },
                "happy": {
                    "low": ["shows a slight smile", "seems pleased"],
                    "medium": ["grins widely", "shows obvious joy"],
                    "high": ["beams with elation", "radiates pure happiness"],
                },
                "sad": {
                    "low": [
                        "looks somewhat downcast",
                        "shows a hint of sadness",
                    ],
                    "medium": [
                        "appears clearly saddened",
                        "displays obvious grief",
                    ],
                    "high": ["is overcome with sorrow", "weeps openly"],
                },
                "fearful": {
                    "low": ["shows slight nervousness", "appears cautious"],
                    "medium": ["displays clear fear", "shows obvious anxiety"],
                    "high": [
                        "is gripped by terror",
                        "trembles with overwhelming fear",
                    ],
                },
                "excited": {
                    "low": ["shows mild interest", "appears somewhat eager"],
                    "medium": [
                        "displays enthusiasm",
                        "shows clear excitement",
                    ],
                    "high": [
                        "buzzes with energy",
                        "vibrates with intense excitement",
                    ],
                },
            }

            # Determine intensity level
            if intensity < 0.3:
                intensity_level = "low"
            elif intensity < 0.7:
                intensity_level = "medium"
            else:
                intensity_level = "high"

            # Get templates for emotion and intensity
            templates = emotion_templates.get(emotion, {}).get(
                intensity_level, ["experiences emotions"]
            )

            # Select and personalize
            base_response = random.choice(templates)

            # Add character name and personality influence
            character_name = context.get("basic_info", {}).get(
                "name", "The character"
            )
            personality = context.get("personality", {})

            # Modify based on personality
            if personality.get("emotional_expression", 0.5) > 0.7:
                # High emotional expression - amplify
                amplifiers = ["openly", "dramatically", "intensely"]
                base_response = f"{random.choice(amplifiers)} {base_response}"
            elif personality.get("emotional_expression", 0.5) < 0.3:
                # Low emotional expression - subdue
                subdued_versions = {
                    "angry": "maintains a stern expression",
                    "happy": "shows subtle satisfaction",
                    "sad": "maintains composure despite sadness",
                    "fearful": "remains outwardly calm despite concern",
                    "excited": "shows controlled enthusiasm",
                }
                base_response = subdued_versions.get(
                    emotion, "shows restraint"
                )

            return f"{character_name} {base_response}."

        except Exception as e:
            self.logger.error(f"Emotional response generation failed: {e}")
            return f"{context.get('basic_info', {}).get('name', 'The character')} reacts emotionally."

    async def get_generation_statistics(self) -> Dict[str, Any]:
        """Get comprehensive generation statistics."""
        try:
            total = self._stats["total_generated"]

            return {
                "total_responses_generated": total,
                "responses_by_category": self._stats["by_category"].copy(),
                "responses_by_tone": self._stats["by_tone"].copy(),
                "template_usage": self._stats["template_used"],
                "fallback_usage": self._stats["fallback_used"],
                "template_success_rate": (
                    (self._stats["template_used"] / total)
                    if total > 0
                    else 0.0
                ),
                "available_templates": len(self._templates),
                "configuration": self._config.copy(),
            }

        except Exception as e:
            self.logger.error(f"Statistics calculation failed: {e}")
            return {"error": str(e)}

    # Private helper methods

    async def _update_character_data(self, context: Dict[str, Any]) -> None:
        """Update character data from context."""
        try:
            self._personality = context.get("personality", {})
            self._faction_beliefs = context.get("faction_info", {}).get(
                "beliefs", {}
            )
            self._current_emotional_state = context.get("state", {}).get(
                "emotional_state", "neutral"
            )

        except Exception as e:
            self.logger.debug(f"Character data update failed: {e}")

    async def _determine_response_category(
        self, context: Dict[str, Any]
    ) -> ResponseCategory:
        """Determine appropriate response category from context."""
        try:
            # Check threat level
            threat_level = context.get("threat_level", ThreatLevel.NEGLIGIBLE)
            if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
                return ResponseCategory.COMBAT

            # Check recent events
            recent_events = context.get("recent_events", [])
            if recent_events:
                last_event = recent_events[-1] if recent_events else None
                if last_event:
                    event_type = (
                        last_event.get("event_type", "")
                        if isinstance(last_event, dict)
                        else getattr(last_event, "event_type", "")
                    )

                    if "battle" in event_type or "attack" in event_type:
                        return ResponseCategory.COMBAT
                    elif (
                        "negotiate" in event_type or "diplomacy" in event_type
                    ):
                        return ResponseCategory.DIPLOMATIC
                    elif "explore" in event_type or "discover" in event_type:
                        return ResponseCategory.EXPLORATION

            # Check emotional state
            if self._current_emotional_state in [
                "angry",
                "fearful",
                "excited",
            ]:
                return ResponseCategory.EMOTIONAL

            # Default to social
            return ResponseCategory.SOCIAL

        except Exception as e:
            self.logger.debug(f"Category determination failed: {e}")
            return ResponseCategory.SOCIAL

    async def _determine_response_tone(
        self, context: Dict[str, Any], category: ResponseCategory
    ) -> ResponseTone:
        """Determine appropriate response tone."""
        try:
            # Personality-based tone
            aggression = self._personality.get("aggression", 0.5)
            intelligence = self._personality.get("intelligence", 0.5)
            formality = self._personality.get("formality", 0.5)

            # High aggression tends toward aggressive tone
            if aggression > 0.7 and category == ResponseCategory.COMBAT:
                return ResponseTone.AGGRESSIVE

            # High intelligence tends toward analytical
            if intelligence > 0.7:
                return ResponseTone.ANALYTICAL

            # High formality tends toward formal tone
            if formality > 0.7:
                return ResponseTone.FORMAL

            # Emotional state influence
            if self._current_emotional_state in ["angry", "frustrated"]:
                return ResponseTone.AGGRESSIVE
            elif self._current_emotional_state in ["sad", "worried"]:
                return ResponseTone.CAUTIOUS
            elif self._current_emotional_state in ["happy", "confident"]:
                return ResponseTone.CONFIDENT

            # Category defaults
            category_tone_defaults = {
                ResponseCategory.COMBAT: ResponseTone.AGGRESSIVE,
                ResponseCategory.DIPLOMATIC: ResponseTone.DIPLOMATIC,
                ResponseCategory.EXPLORATION: ResponseTone.CAUTIOUS,
                ResponseCategory.EMOTIONAL: ResponseTone.EMOTIONAL,
                ResponseCategory.INFORMATIONAL: ResponseTone.ANALYTICAL,
            }

            return category_tone_defaults.get(category, ResponseTone.CASUAL)

        except Exception as e:
            self.logger.debug(f"Tone determination failed: {e}")
            return ResponseTone.CASUAL

    async def _find_matching_templates(
        self,
        category: ResponseCategory,
        tone: ResponseTone,
        context: Dict[str, Any],
    ) -> List[ResponseTemplate]:
        """Find templates that match the given criteria."""
        try:
            matching_templates = []

            category_templates = self._templates.get(category, [])

            for template in category_templates:
                if template.tone == tone:
                    match_score = template.matches_context(
                        self._personality, self._faction_beliefs, context
                    )

                    if (
                        match_score
                        >= self._config["template_selection_threshold"]
                    ):
                        matching_templates.append(template)

            # Sort by match score
            matching_templates.sort(
                key=lambda t: t.matches_context(
                    self._personality, self._faction_beliefs, context
                ),
                reverse=True,
            )

            return matching_templates

        except Exception as e:
            self.logger.debug(f"Template matching failed: {e}")
            return []

    async def _generate_from_template(
        self, template: ResponseTemplate, context: Dict[str, Any]
    ) -> str:
        """Generate response from template."""
        try:
            # Select random template from the list
            template_text = random.choice(template.templates)

            # Replace placeholders
            response = await self._replace_placeholders(template_text, context)

            return response

        except Exception as e:
            self.logger.debug(f"Template generation failed: {e}")
            return "I consider the situation carefully."

    async def _generate_fallback_response(
        self,
        category: ResponseCategory,
        tone: ResponseTone,
        context: Dict[str, Any],
    ) -> str:
        """Generate fallback response when no templates match."""
        try:
            # Basic fallback templates by category
            fallback_templates = {
                ResponseCategory.COMBAT: [
                    "I prepare for whatever comes next.",
                    "I ready myself for action.",
                    "I assess the threat before me.",
                ],
                ResponseCategory.SOCIAL: [
                    "I consider how to respond to this situation.",
                    "I think about the best way forward.",
                    "I weigh my options carefully.",
                ],
                ResponseCategory.EXPLORATION: [
                    "I examine my surroundings with interest.",
                    "I look around to better understand this place.",
                    "I take note of what I see here.",
                ],
                ResponseCategory.DIPLOMATIC: [
                    "I consider the best diplomatic approach.",
                    "I think about how to handle this delicately.",
                    "I weigh the political implications.",
                ],
                ResponseCategory.EMOTIONAL: [
                    "I feel the weight of this moment.",
                    "My emotions run deep in this situation.",
                    "This situation stirs something within me.",
                ],
            }

            templates = fallback_templates.get(
                category,
                [
                    "I pause to consider the situation.",
                    "I think about what to do next.",
                    "I reflect on the circumstances before me.",
                ],
            )

            base_response = random.choice(templates)

            # Apply tone modifications
            if tone == ResponseTone.AGGRESSIVE:
                base_response = base_response.replace(
                    "I consider", "I determine"
                )
                base_response = base_response.replace("I think", "I decide")
            elif tone == ResponseTone.FORMAL:
                base_response = base_response.replace("I ", "I shall ")

            return base_response

        except Exception as e:
            self.logger.debug(f"Fallback generation failed: {e}")
            return "I consider my next move."

    async def _enhance_with_personality(
        self, response: str, context: Dict[str, Any]
    ) -> str:
        """Enhance response with personality-specific language."""
        try:
            enhanced = response

            # Intelligence-based vocabulary
            intelligence = self._personality.get("intelligence", 0.5)
            if intelligence > 0.7:
                # Use more sophisticated vocabulary
                replacements = {
                    "think": "analyze",
                    "see": "observe",
                    "go": "proceed",
                    "look": "examine",
                }
                for simple, complex in replacements.items():
                    enhanced = enhanced.replace(simple, complex)

            # Aggression-based modifications
            aggression = self._personality.get("aggression", 0.5)
            if aggression > 0.7:
                # Add more decisive language
                enhanced = enhanced.replace("consider", "determine")
                enhanced = enhanced.replace("might", "will")

            # Formality modifications
            formality = self._personality.get("formality", 0.5)
            if formality > 0.7:
                # Make more formal
                enhanced = enhanced.replace("I'll", "I shall")
                enhanced = enhanced.replace("can't", "cannot")
            elif formality < 0.3:
                # Make more casual
                enhanced = enhanced.replace("I shall", "I'll")
                enhanced = enhanced.replace("cannot", "can't")

            return enhanced

        except Exception as e:
            self.logger.debug(f"Personality enhancement failed: {e}")
            return response

    async def _apply_emotional_modifiers(
        self, response: str, context: Dict[str, Any]
    ) -> str:
        """Apply emotional modifiers to response."""
        try:
            if self._current_emotional_state == "neutral":
                return response

            # Emotional modifiers
            modifiers = {
                "angry": {
                    "prefixes": ["With growing frustration,", "Angrily,"],
                    "replacements": {
                        "consider": "demand to know",
                        "think": "realize",
                    },
                },
                "fearful": {
                    "prefixes": ["Nervously,", "With caution,"],
                    "replacements": {
                        "move": "carefully advance",
                        "look": "peer anxiously",
                    },
                },
                "excited": {
                    "prefixes": ["Eagerly,", "With enthusiasm,"],
                    "replacements": {
                        "go": "rush toward",
                        "see": "spot with interest",
                    },
                },
                "sad": {
                    "prefixes": ["Heavily,", "With a heavy heart,"],
                    "replacements": {"consider": "reluctantly think about"},
                },
            }

            emotion_modifier = modifiers.get(self._current_emotional_state)
            if emotion_modifier:
                # Add emotional prefix sometimes
                if random.random() < 0.3:  # 30% chance
                    prefix = random.choice(emotion_modifier["prefixes"])
                    response = f"{prefix} {response.lower()}"

                # Apply word replacements
                for original, replacement in emotion_modifier[
                    "replacements"
                ].items():
                    response = response.replace(original, replacement)

            return response

        except Exception as e:
            self.logger.debug(f"Emotional modifier application failed: {e}")
            return response

    async def _format_and_validate(self, response: str) -> str:
        """Format and validate final response."""
        try:
            # Clean up spacing
            formatted = " ".join(response.split())

            # Ensure proper capitalization
            if formatted and formatted[0].islower():
                formatted = formatted[0].upper() + formatted[1:]

            # Ensure proper punctuation
            if formatted and formatted[-1] not in ".!?":
                formatted += "."

            # Validate length
            if len(formatted) < self._config["min_response_length"]:
                formatted += (
                    " I take a moment to consider the situation further."
                )
            elif len(formatted) > self._config["max_response_length"]:
                # Truncate at sentence boundary
                sentences = formatted.split(".")
                truncated = sentences[0] + "."
                if len(truncated) <= self._config["max_response_length"]:
                    formatted = truncated

            return formatted

        except Exception as e:
            self.logger.debug(f"Response formatting failed: {e}")
            return response

    async def _replace_placeholders(
        self, template: str, context: Dict[str, Any]
    ) -> str:
        """Replace placeholders in template with context values."""
        try:
            # Common placeholders
            placeholders = {
                "{character_name}": context.get("basic_info", {}).get(
                    "name", "I"
                ),
                "{faction}": context.get("faction_info", {}).get(
                    "faction", "Independent"
                ),
                "{location}": context.get("state", {}).get(
                    "current_location", "here"
                ),
                "{threat_level}": str(context.get("threat_level", "unknown")),
            }

            result = template
            for placeholder, value in placeholders.items():
                result = result.replace(placeholder, str(value))

            return result

        except Exception as e:
            self.logger.debug(f"Placeholder replacement failed: {e}")
            return template

    async def _get_emergency_response(self) -> str:
        """Get emergency response when all else fails."""
        return "I pause to gather my thoughts."

    def _initialize_response_templates(self) -> None:
        """Initialize response template library."""
        # Combat templates
        self._templates[ResponseCategory.COMBAT] = [
            ResponseTemplate(
                category=ResponseCategory.COMBAT,
                tone=ResponseTone.AGGRESSIVE,
                templates=[
                    "I ready my weapon and prepare to strike down any who oppose me.",
                    "The time for words has passed. I advance with deadly intent.",
                    "I will not yield ground to these enemies.",
                ],
                personality_weights={"aggression": 1.0, "courage": 0.5},
                faction_weights={"militaristic": 0.7},
                context_requirements=["threat_level"],
            ),
            ResponseTemplate(
                category=ResponseCategory.COMBAT,
                tone=ResponseTone.CAUTIOUS,
                templates=[
                    "I assess the tactical situation before committing to action.",
                    "Caution guides my approach to this dangerous situation.",
                    "I prepare my defenses while watching for opportunities.",
                ],
                personality_weights={"intelligence": 0.8, "aggression": -0.3},
                faction_weights={"strategic": 0.6},
                context_requirements=["threat_level"],
            ),
        ]

        # Social templates
        self._templates[ResponseCategory.SOCIAL] = [
            ResponseTemplate(
                category=ResponseCategory.SOCIAL,
                tone=ResponseTone.DIPLOMATIC,
                templates=[
                    "I believe we can find common ground through respectful dialogue.",
                    "Perhaps we should consider all perspectives before proceeding.",
                    "I'm interested in understanding your position on this matter.",
                ],
                personality_weights={"charisma": 0.8, "intelligence": 0.5},
                faction_weights={"diplomacy": 0.7},
                context_requirements=[],
            ),
            ResponseTemplate(
                category=ResponseCategory.SOCIAL,
                tone=ResponseTone.CASUAL,
                templates=[
                    "I think we should just take this one step at a time.",
                    "Let's see what happens and adapt as we go.",
                    "I'm curious to hear what others think about this.",
                ],
                personality_weights={"formality": -0.5, "adaptability": 0.6},
                faction_weights={},
                context_requirements=[],
            ),
        ]

        # Add more templates for other categories...
        # This is a simplified version - full implementation would have many
        # more templates

    def _initialize_vocabulary(self) -> Dict[str, List[str]]:
        """Initialize vocabulary alternatives for different intelligence levels."""
        return {
            "basic": [
                "see",
                "go",
                "think",
                "know",
                "want",
                "get",
                "make",
                "look",
                "find",
            ],
            "advanced": [
                "observe",
                "proceed",
                "analyze",
                "comprehend",
                "desire",
                "acquire",
                "construct",
                "examine",
                "locate",
            ],
            "sophisticated": [
                "perceive",
                "advance",
                "contemplate",
                "understand",
                "aspire",
                "obtain",
                "fabricate",
                "scrutinize",
                "discern",
            ],
        }

    def _initialize_phrase_libraries(self) -> Dict[str, List[str]]:
        """Initialize phrase libraries for different contexts."""
        return {
            "uncertainty": [
                "I'm not entirely sure",
                "It's difficult to say",
                "I have my doubts",
            ],
            "confidence": [
                "I'm certain that",
                "Without question",
                "I have no doubt",
            ],
            "urgency": [
                "Time is of the essence",
                "We must act quickly",
                "This cannot wait",
            ],
            "caution": [
                "We should be careful",
                "Prudence suggests",
                "It would be wise to",
            ],
        }
