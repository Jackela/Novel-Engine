import pytest

from src.core.character_decision_maker import DecisionMaker, ThreatLevel

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_make_decision_returns_action_when_score_above_threshold():
    maker = DecisionMaker(agent_id="agent_1")

    world_state_update = {
        "recent_events": [{"description": "Hostile attack reported"}],
        "current_location": "Sector 7",
        "weather": "clear",
    }
    character_data = {
        "faction": "Test Faction",
        "rank_role": "Scout",
        "capabilities": {"combat": True},
        "psychological": {"traits": {"decisive": 0.8}},
    }
    subjective_worldview = {
        "known_entities": {"enemy": {"disposition": "hostile"}},
        "current_mission": {"description": "Secure the area", "progress": 0.2},
        "relationships": {},
    }
    personality_traits = {"aggressive": 1.0, "cautious": 0.0}
    decision_weights = {"mission_success": 0.8}

    action = maker.make_decision(
        world_state_update=world_state_update,
        character_data=character_data,
        personality_traits=personality_traits,
        decision_weights=decision_weights,
        subjective_worldview=subjective_worldview,
    )

    assert action is not None
    assert action.action_type in {"attack", "defend", "retreat", "observe", "move"}
    assert action.priority.name in {"CRITICAL", "HIGH"}
    assert maker.decision_history


@pytest.mark.unit
def test_make_decision_returns_none_when_scores_below_threshold():
    maker = DecisionMaker(agent_id="agent_2")

    world_state_update = {"recent_events": []}
    character_data = {
        "faction": "Test Faction",
        "rank_role": "Engineer",
        "capabilities": {},
        "psychological": {"traits": {"decisive": 0.0}},
    }
    subjective_worldview = {"known_entities": {}, "relationships": {}}
    personality_traits = {"aggressive": 0.2, "cautious": 0.8}
    decision_weights = {"mission_success": 0.4}

    action = maker.make_decision(
        world_state_update=world_state_update,
        character_data=character_data,
        personality_traits=personality_traits,
        decision_weights=decision_weights,
        subjective_worldview=subjective_worldview,
    )

    assert action is None


@pytest.mark.unit
def test_threat_level_detection_prefers_hostile_signals():
    maker = DecisionMaker(agent_id="agent_3")

    world_state_update = {
        "recent_events": [{"description": "Major hostile attack in sector"}],
    }
    worldview = {
        "known_entities": {
            "hostile_1": {"disposition": "hostile"},
            "hostile_2": {"disposition": "hostile"},
        }
    }

    threat = maker._assess_overall_threat_level(world_state_update, worldview)

    assert threat in {ThreatLevel.HIGH, ThreatLevel.CRITICAL}
