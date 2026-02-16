from types import SimpleNamespace

import pytest

from src.agents.agent_lifecycle_manager import AgentLifecycleManager
from src.core.types.shared_types import (
    ActionParameters,
    ActionTarget,
    ActionType,
    EntityType,
    ProposedAction,
    ValidationResult,
)

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_adjudicate_action_records_successful_validation():
    manager = AgentLifecycleManager()
    agent = SimpleNamespace(agent_id="agent_1")

    action = ProposedAction(
        action_id="action_ok",
        character_id="agent_1",
        action_type=ActionType.OBSERVE,
        target=ActionTarget(entity_id="zone_alpha", entity_type=EntityType.LOCATION),
        parameters=ActionParameters(),
        reasoning="Observe the surroundings for any changes.",
    )

    result = manager.adjudicate_agent_action(agent, action)

    assert result.success is True
    assert result.violations == []
    assert result.validated_action.validation_result == ValidationResult.VALID
    metrics = manager.get_lifecycle_metrics()
    assert metrics["successful_actions"] == 1
    assert metrics["failed_actions"] == 0


@pytest.mark.unit
def test_adjudicate_action_repairs_missing_target_and_reasoning():
    manager = AgentLifecycleManager()
    agent = SimpleNamespace(agent_id="agent_2")

    action = ProposedAction(
        action_id="action_needs_repair",
        character_id="agent_2",
        action_type=ActionType.WAIT,
        target=None,
        parameters=ActionParameters(),
        reasoning="",
    )

    result = manager.adjudicate_agent_action(agent, action)

    assert result.success is True
    assert result.violations
    assert any("Added default target" in entry for entry in result.repair_log)
    assert any(
        "Added default narrative reasoning" in entry for entry in result.repair_log
    )
    assert manager.violation_history
    assert manager.repair_attempts_count == 1
