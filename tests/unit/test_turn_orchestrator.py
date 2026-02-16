from datetime import datetime
from types import SimpleNamespace

import pytest

from src.core.event_bus import EventBus
from src.core.turn_orchestrator import TurnOrchestrator
from src.core.types.shared_types import CharacterAction

pytestmark = pytest.mark.unit


class DummyAgent:
    def __init__(
        self, agent_id: str, refresh_result: bool, *, raise_error: bool = False
    ):
        self.agent_id = agent_id
        self.character_data = {"name": f"Agent {agent_id}"}
        self.core = SimpleNamespace(
            character_data={
                "enhanced_context": True,
                "context_load_success": refresh_result,
            }
        )
        self._refresh_result = refresh_result
        self._raise_error = raise_error

    async def refresh_context(self) -> bool:
        if self._raise_error:
            raise RuntimeError("refresh failed")
        return self._refresh_result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_turn_tracks_context_refresh_and_emits_event():
    event_bus = EventBus()
    orchestrator = TurnOrchestrator(event_bus, max_turn_history=2)
    log_entries: list[str] = []

    agents = [
        DummyAgent("agent_a", True),
        DummyAgent("agent_b", False, raise_error=True),
    ]

    result = await orchestrator.run_turn(agents, {"seed": "data"}, log_entries.append)

    assert result["status"] == "turn_started"
    assert result["context_results"]["successful_refreshes"] == 1
    assert result["context_results"]["failed_refreshes"] == 1
    assert len(event_bus.get_history(event_type="TURN_START")) == 1
    assert orchestrator.current_turn_state is not None
    assert orchestrator.current_turn_state.world_state_updates["context_enhanced"]


@pytest.mark.unit
def test_handle_agent_action_records_wait_and_action():
    event_bus = EventBus()
    orchestrator = TurnOrchestrator(event_bus)
    log_entries: list[str] = []

    agent = DummyAgent("agent_a", True)
    orchestrator.current_turn_state = SimpleNamespace(
        turn_number=1,
        start_time=datetime.now(),
        agents_processed=[],
        actions_received=[],
        world_state_updates={},
        narrative_events=[],
        completed=False,
    )

    action = CharacterAction(action_type="move", reasoning="Advance", priority="normal")
    assert orchestrator.handle_agent_action(agent, action, log_entries.append)
    assert orchestrator.total_actions_processed == 1
    assert len(orchestrator.current_turn_state.actions_received) == 1

    assert orchestrator.handle_agent_action(agent, None, log_entries.append)
    assert len(orchestrator.current_turn_state.actions_received) == 2
    assert "waiting" in log_entries[-1].lower()


@pytest.mark.unit
def test_turn_history_and_performance_metrics():
    event_bus = EventBus()
    orchestrator = TurnOrchestrator(event_bus, max_turn_history=1)

    orchestrator.current_turn_state = SimpleNamespace(
        turn_number=1,
        start_time=datetime.now(),
        agents_processed=["agent_a"],
        actions_received=[{"action": "move"}],
        world_state_updates={},
        narrative_events=[],
        completed=False,
    )

    orchestrator._finalize_turn()
    history = orchestrator.get_turn_history()
    assert len(history) == 1
    assert history[0]["turn_number"] == 1

    metrics = orchestrator.get_performance_metrics()
    assert metrics["total_turns_executed"] == 1
    assert metrics["history_size"] == 1
