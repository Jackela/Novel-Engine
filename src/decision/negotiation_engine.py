"""
Negotiation Engine

Evaluates user free-text input for feasibility and generates
adjusted actions or alternatives when needed.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .models import (
    DecisionOption,
    DecisionPoint,
    FeasibilityResult,
    NegotiationResult,
    UserDecision,
)

logger = logging.getLogger(__name__)


# Prompt template for feasibility evaluation
EVALUATION_PROMPT = """You are a narrative consistency checker for an interactive story.

## Current Story Context
{narrative_context}

## Characters Available
{characters}

## Current Decision Point
Type: {decision_type}
Description: {decision_description}

## User's Requested Action
"{user_input}"

## Task
Evaluate if this action is feasible within the story context. Consider:
1. Does it fit the current narrative situation?
2. Can the characters realistically do this?
3. Does it maintain story consistency?
4. Is it appropriate for the tone/genre?

Respond in JSON format:
{{
    "feasibility": "accepted" | "minor_adjustment" | "alternative_required" | "rejected",
    "explanation": "Brief explanation of your evaluation",
    "adjusted_action": "If adjustment needed, the modified action (null if accepted or rejected)",
    "alternatives": [
        {{"label": "Alternative 1", "description": "Description"}},
        {{"label": "Alternative 2", "description": "Description"}}
    ]
}}

Only provide alternatives if feasibility is "alternative_required" or "rejected".
Keep explanations concise (1-2 sentences).
"""


class NegotiationEngine:
    """
    Evaluates user free-text input and negotiates feasible actions.

    Uses LLM to:
    1. Check if user's requested action is feasible
    2. Suggest adjustments if needed
    3. Propose alternatives if action cannot be executed
    """

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Initialize the negotiation engine.

        Args:
            llm_client: LLM client for evaluation (optional, uses simple rules if None)
        """
        self._llm_client = llm_client

    async def evaluate_input(
        self,
        user_decision: UserDecision,
        decision_point: DecisionPoint,
        world_state: Optional[Dict[str, Any]] = None,
        characters: Optional[List[Dict[str, Any]]] = None,
    ) -> NegotiationResult:
        """
        Evaluate user's free-text input for feasibility.

        Args:
            user_decision: The user's decision with free_text
            decision_point: The decision point being responded to
            world_state: Current world state for context
            characters: Available characters

        Returns:
            NegotiationResult with evaluation and suggestions
        """
        if not user_decision.free_text:
            # No free text to evaluate
            return NegotiationResult(
                decision_id=user_decision.decision_id,
                feasibility=FeasibilityResult.ACCEPTED,
            )

        user_input = user_decision.free_text.strip()

        # Quick validation
        if len(user_input) < 5:
            return NegotiationResult(
                decision_id=user_decision.decision_id,
                feasibility=FeasibilityResult.REJECTED,
                explanation="Input too short. Please provide more detail.",
            )

        if len(user_input) > 500:
            return NegotiationResult(
                decision_id=user_decision.decision_id,
                feasibility=FeasibilityResult.MINOR_ADJUSTMENT,
                explanation="Input is quite long. It will be summarized.",
                adjusted_action=user_input[:500] + "...",
            )

        # Use LLM if available
        if self._llm_client:
            return await self._evaluate_with_llm(
                user_input=user_input,
                decision_point=decision_point,
                world_state=world_state,
                characters=characters,
            )

        # Fallback: simple rule-based evaluation
        return self._evaluate_with_rules(
            user_input=user_input,
            decision_point=decision_point,
        )

    async def _evaluate_with_llm(
        self,
        user_input: str,
        decision_point: DecisionPoint,
        world_state: Optional[Dict[str, Any]],
        characters: Optional[List[Dict[str, Any]]],
    ) -> NegotiationResult:
        """Use LLM to evaluate the user input."""
        try:
            # Build prompt
            characters_str = "None specified"
            if characters:
                characters_str = ", ".join(
                    c.get("name", c.get("id", "Unknown")) for c in characters
                )

            prompt = EVALUATION_PROMPT.format(
                narrative_context=decision_point.narrative_context
                or "Story in progress",
                characters=characters_str,
                decision_type=decision_point.decision_type.value,
                decision_description=decision_point.description,
                user_input=user_input,
            )

            # Call LLM
            response = await self._llm_client.generate(prompt)

            # Parse response
            return self._parse_llm_response(
                response=response,
                decision_id=decision_point.decision_id,
            )

        except Exception as e:
            logger.error("LLM evaluation failed: %s", e)
            # Fallback to rule-based
            return self._evaluate_with_rules(user_input, decision_point)

    def _parse_llm_response(
        self,
        response: str,
        decision_id: str,
    ) -> NegotiationResult:
        """Parse LLM response into NegotiationResult."""
        try:
            # Extract JSON from response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if not json_match:
                raise ValueError("No JSON found in response")

            data = json.loads(json_match.group())

            # Parse feasibility
            feasibility_str = data.get("feasibility", "accepted").lower()
            feasibility_map = {
                "accepted": FeasibilityResult.ACCEPTED,
                "minor_adjustment": FeasibilityResult.MINOR_ADJUSTMENT,
                "alternative_required": FeasibilityResult.ALTERNATIVE_REQUIRED,
                "rejected": FeasibilityResult.REJECTED,
            }
            feasibility = feasibility_map.get(
                feasibility_str, FeasibilityResult.ACCEPTED
            )

            # Parse alternatives
            alternatives = []
            for i, alt in enumerate(data.get("alternatives", [])[:4]):
                alternatives.append(
                    DecisionOption(
                        option_id=100 + i,  # High IDs for alternatives
                        label=alt.get("label", f"Alternative {i+1}"),
                        description=alt.get("description", ""),
                    )
                )

            return NegotiationResult(
                decision_id=decision_id,
                feasibility=feasibility,
                explanation=data.get("explanation", ""),
                adjusted_action=data.get("adjusted_action"),
                alternatives=alternatives,
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse LLM response: %s", e)
            return NegotiationResult(
                decision_id=decision_id,
                feasibility=FeasibilityResult.ACCEPTED,
                explanation="Evaluation complete.",
            )

    def _evaluate_with_rules(
        self,
        user_input: str,
        decision_point: DecisionPoint,
    ) -> NegotiationResult:
        """Simple rule-based evaluation when LLM is not available."""
        user_input_lower = user_input.lower()

        # Check for problematic keywords
        rejected_keywords = [
            "kill everyone",
            "destroy world",
            "god mode",
            "cheat",
            "teleport",
            "time travel",
            "become immortal",
        ]
        for keyword in rejected_keywords:
            if keyword in user_input_lower:
                return NegotiationResult(
                    decision_id=decision_point.decision_id,
                    feasibility=FeasibilityResult.REJECTED,
                    explanation=f"Action '{keyword}' is not possible within story rules.",
                    alternatives=self._get_default_alternatives(),
                )

        # Check for actions that might need adjustment
        adjustment_keywords = [
            "fly",
            "magic",
            "superpowers",
            "instantly",
        ]
        for keyword in adjustment_keywords:
            if keyword in user_input_lower:
                return NegotiationResult(
                    decision_id=decision_point.decision_id,
                    feasibility=FeasibilityResult.MINOR_ADJUSTMENT,
                    explanation=f"'{keyword}' may not be available. Action adjusted for realism.",
                    adjusted_action=self._make_realistic(user_input),
                )

        # Default: accept the input
        return NegotiationResult(
            decision_id=decision_point.decision_id,
            feasibility=FeasibilityResult.ACCEPTED,
            explanation="Your action has been accepted.",
        )

    def _make_realistic(self, user_input: str) -> str:
        """Attempt to make an action more realistic."""
        # Simple replacements
        replacements = {
            "fly": "move quickly",
            "teleport": "rush",
            "magic": "skill",
            "instantly": "quickly",
            "superpowers": "abilities",
        }
        result = user_input
        for old, new in replacements.items():
            result = re.sub(rf"\b{old}\b", new, result, flags=re.IGNORECASE)
        return result

    def _get_default_alternatives(self) -> List[DecisionOption]:
        """Get default alternative options."""
        return [
            DecisionOption(
                option_id=100,
                label="Try a different approach",
                description="Consider a more feasible action",
            ),
            DecisionOption(
                option_id=101,
                label="Ask for suggestions",
                description="Let the AI suggest possible actions",
            ),
        ]

    def set_llm_client(self, llm_client: Any):
        """Set or update the LLM client."""
        self._llm_client = llm_client
