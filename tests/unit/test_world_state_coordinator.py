import json

import pytest

from src.core.world_state_coordinator import WorldStateCoordinator

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_world_state_defaults_and_feedback_generation(tmp_path):
    coordinator = WorldStateCoordinator()

    coordinator.record_agent_discovery("agent_1", "Hidden cache", 1)
    coordinator.record_environmental_change("default_area", "Dust storm rising")

    feedback = coordinator.generate_world_state_feedback("agent_1")
    assert feedback is not None
    assert "personal_discoveries" in feedback
    assert "environmental_changes" in feedback
    assert "world_state_summary" in feedback

    world_state = coordinator.get_world_state_for_agent("agent_1", 1, 2)
    assert "agent_feedback" in world_state
    assert world_state["current_turn"] == 1

    summary = coordinator.get_world_state_summary()
    assert summary["tracked_agents"] == 1
    assert summary["environmental_changes"] == 1


@pytest.mark.unit
def test_missing_world_state_file_creates_default(tmp_path):
    state_path = tmp_path / "world_state.json"
    _unused_coordinator = WorldStateCoordinator(
        str(state_path)
    )  # noqa: F841 - side effect creates file

    assert state_path.exists()
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert "world_state_tracker" in saved
    assert "locations" in saved


@pytest.mark.unit
def test_invalid_world_state_json_raises(tmp_path):
    state_path = tmp_path / "bad_state.json"
    state_path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(ValueError):
        WorldStateCoordinator(str(state_path))


@pytest.mark.unit
def test_save_world_state_persists_tracker(tmp_path):
    state_path = tmp_path / "state.json"
    coordinator = WorldStateCoordinator()

    assert coordinator.save_world_state(str(state_path)) is True
    saved = json.loads(state_path.read_text(encoding="utf-8"))
    assert "last_saved" in saved
    assert "world_state_tracker" in saved
