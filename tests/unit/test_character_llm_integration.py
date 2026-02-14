from unittest.mock import patch

import pytest

from src.core.character_llm_integration import LLMIntegration
from src.core.types.shared_types import ActionPriority

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_enhanced_decision_making_parses_llm_response():
    integration = LLMIntegration(agent_id="agent_1")

    world_state_update = {"current_turn": 1, "world_state": {"current_turn": 1}}
    situation_assessment = {
        "threat_level": "low",
        "current_goals": [],
        "available_resources": {},
        "social_obligations": [],
        "mission_status": {},
        "environmental_factors": {},
    }
    available_actions = [{"type": "move", "description": "Move to a new spot"}]
    character_data = {"name": "Agent One", "rank_role": "Scout"}
    personality_traits = {"brave": 0.7}
    decision_weights = {"mission_success": 0.7}
    subjective_worldview = {"primary_faction": "Test Faction", "known_entities": {}}

    llm_response = "ACTION: move\nTARGET: gate\nREASONING: urgent relocation"

    with patch.object(LLMIntegration, "_call_llm", return_value=llm_response):
        action = integration.enhanced_decision_making(
            world_state_update=world_state_update,
            situation_assessment=situation_assessment,
            available_actions=available_actions,
            character_data=character_data,
            personality_traits=personality_traits,
            decision_weights=decision_weights,
            subjective_worldview=subjective_worldview,
            current_status="active",
            morale_level=0.9,
            current_location="Sector 7",
            relationships={"ally": 0.6},
        )

    assert action is not None
    assert action.action_type == "move"
    assert action.target == "gate"
    assert action.priority == ActionPriority.CRITICAL
    assert integration.prompt_history


@pytest.mark.unit
def test_parse_llm_response_rejects_invalid_format():
    integration = LLMIntegration(agent_id="agent_2")

    result = integration._parse_llm_response("nonsense", [{"type": "move"}])

    assert result is None


@pytest.mark.unit
def test_priority_detection_rules():
    integration = LLMIntegration(agent_id="agent_3")

    assert (
        integration._determine_llm_action_priority("attack", "urgent need to respond")
        == ActionPriority.CRITICAL
    )
    assert (
        integration._determine_llm_action_priority(
            "communicate", "must report to command"
        )
        == ActionPriority.HIGH
    )
    assert (
        integration._determine_llm_action_priority("communicate", "share the update")
        == ActionPriority.MEDIUM
    )
    assert (
        integration._determine_llm_action_priority("observe", "gather details")
        == ActionPriority.LOW
    )
