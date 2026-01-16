import pytest
from types import SimpleNamespace

from src.core.iron_laws_processor import IronLawsProcessor
from src.core.types.shared_types import (
    ActionIntensity,
    ActionParameters,
    ActionTarget,
    ActionType,
    CharacterData,
    CharacterResources,
    CharacterStats,
    EntityType,
    Position,
    ProposedAction,
    ResourceValue,
    ValidationResult,
)


def _build_character_data(
    *,
    stamina_current: float = 50.0,
    equipment: list[str] | None = None,
    position: Position | None = None,
) -> CharacterData:
    return CharacterData(
        character_id="agent_1",
        name="Agent One",
        faction="Test",
        position=position or Position(x=0.0, y=0.0, z=0.0),
        stats=CharacterStats(
            strength=7,
            dexterity=7,
            intelligence=6,
            willpower=6,
            perception=6,
            charisma=5,
        ),
        resources=CharacterResources(
            health=ResourceValue(current=100.0, maximum=100.0),
            stamina=ResourceValue(current=stamina_current, maximum=100.0),
            morale=ResourceValue(current=50.0, maximum=100.0),
        ),
        equipment=equipment or [],
    )


@pytest.mark.unit
def test_adjudicate_action_valid_returns_clean_report():
    processor = IronLawsProcessor()
    character_data = _build_character_data(
        stamina_current=80.0, equipment=["basic_weapon"]
    )
    agent = SimpleNamespace(character_id="agent_1", character_data=character_data)

    action = ProposedAction(
        character_id="agent_1",
        action_type=ActionType.MOVE,
        target=ActionTarget(
            entity_id="nearby_point",
            entity_type=EntityType.LOCATION,
            position=Position(x=1.0, y=1.0, z=0.0),
        ),
        parameters=ActionParameters(
            intensity=ActionIntensity.NORMAL, duration=1.0, range=3.0
        ),
        reasoning="Move to check the area.",
    )

    report = processor.adjudicate_action(action, agent, {})

    assert report.overall_result == ValidationResult.VALID
    assert report.violations == []
    assert report.final_action is None
    assert report.checks_performed


@pytest.mark.unit
def test_adjudicate_action_applies_repairs_for_multiple_violations():
    processor = IronLawsProcessor()
    character_data = _build_character_data(stamina_current=2.0, equipment=[])
    agent = SimpleNamespace(character_id="agent_1", character_data=character_data)

    action = ProposedAction(
        character_id="agent_1",
        action_type=ActionType.ATTACK,
        target=ActionTarget(
            entity_id="ally_commanding_officer",
            entity_type=EntityType.CHARACTER,
            position=Position(x=20.0, y=0.0, z=0.0),
        ),
        parameters=ActionParameters(
            intensity=ActionIntensity.HIGH, duration=1.0, range=1.0
        ),
        reasoning="",
    )

    report = processor.adjudicate_action(action, agent, {})

    assert report.overall_result == ValidationResult.REQUIRES_REPAIR
    assert report.final_action is not None
    assert report.final_action.action_type == ActionType.COMMUNICATE
    assert any(
        "Inserted reasoning" in entry for entry in report.repair_attempts
    )
    assert any(
        "Reduced intensity" in entry for entry in report.repair_attempts
    )
    assert report.final_action.parameters.intensity != ActionIntensity.HIGH
    law_codes = {violation.law_code for violation in report.violations}
    assert {"E001", "E002", "E004", "E005"} <= law_codes


@pytest.mark.unit
def test_adjudicate_action_coerces_unstructured_action_payload():
    processor = IronLawsProcessor()
    character_data = _build_character_data(
        stamina_current=60.0, equipment=["basic_weapon"]
    )
    agent = SimpleNamespace(character_id="agent_1", character_data=character_data)

    raw_action = SimpleNamespace(
        character_id="agent_1",
        action_type="move",
        reasoning="Move now.",
        parameters=SimpleNamespace(intensity="high", duration="2", range="3"),
        target=SimpleNamespace(entity_id="checkpoint", entity_type="location"),
    )

    report = processor.adjudicate_action(raw_action, agent, {})

    assert report.overall_result == ValidationResult.VALID
    assert report.violations == []
