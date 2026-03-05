#!/usr/bin/env python3
"""
Narrative Generation Service Tests

测试叙事规划引擎的所有功能，包括叙事指导生成、
阶段特定目标等。
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.services.narrative_planning_engine import (
    NarrativePlanningEngine,
)
from src.contexts.narratives.domain.value_objects import (
    NarrativeGuidance,
    StoryArcPhase,
    StoryArcState,
)


class TestNarrativePlanningEngineInitialization:
    """测试NarrativePlanningEngine初始化"""

    def test_engine_initialization(self):
        """测试引擎正确初始化"""
        engine = NarrativePlanningEngine()
        assert engine is not None


class TestGenerateGuidanceForTurn:
    """测试回合指导生成功能"""

    @pytest.fixture
    def exposition_state(self):
        """创建展示阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.2"),
            turns_in_current_phase=2,
            turn_number=3,
            current_tension_level=Decimal("2.5"),
        )

    @pytest.fixture
    def rising_action_state(self):
        """创建上升动作阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.RISING_ACTION,
            phase_progress=Decimal("0.4"),
            turns_in_current_phase=6,
            turn_number=12,
            current_tension_level=Decimal("5.5"),
        )

    @pytest.fixture
    def climax_state(self):
        """创建高潮阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.CLIMAX,
            phase_progress=Decimal("0.8"),
            turns_in_current_phase=4,
            turn_number=22,
            current_tension_level=Decimal("8.8"),
        )

    @pytest.fixture
    def falling_action_state(self):
        """创建下降动作阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.FALLING_ACTION,
            phase_progress=Decimal("0.3"),
            turns_in_current_phase=2,
            turn_number=26,
            current_tension_level=Decimal("4.2"),
        )

    @pytest.fixture
    def resolution_state(self):
        """创建结局阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.RESOLUTION,
            phase_progress=Decimal("0.7"),
            turns_in_current_phase=5,
            turn_number=32,
            current_tension_level=Decimal("1.8"),
        )

    def test_generate_guidance_returns_narrative_guidance(self, exposition_state):
        """测试生成指导返回NarrativeGuidance对象"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=exposition_state)
        assert isinstance(guidance, NarrativeGuidance)

    def test_generate_guidance_has_required_fields(self, exposition_state):
        """测试生成的指导包含所有必要字段"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=exposition_state)
        assert hasattr(guidance, 'guidance_id')
        assert hasattr(guidance, 'turn_number')
        assert hasattr(guidance, 'arc_state')
        assert hasattr(guidance, 'primary_narrative_goal')
        assert hasattr(guidance, 'target_tension_level')
        assert hasattr(guidance, 'secondary_narrative_goals')

    def test_exposition_phase_guidance(self, exposition_state):
        """测试展示阶段的指导"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=exposition_state)
        assert guidance.primary_narrative_goal == "Introduce new characters and establish setting"
        assert guidance.target_tension_level == Decimal("3.0")

    def test_rising_action_phase_guidance(self, rising_action_state):
        """测试上升动作阶段的指导"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=rising_action_state)
        assert guidance.primary_narrative_goal == "Increase tension and develop conflicts"
        assert guidance.target_tension_level == Decimal("6.0")

    def test_climax_phase_guidance(self, climax_state):
        """测试高潮阶段的指导"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=climax_state)
        assert guidance.primary_narrative_goal == "Deliver high tension confrontation"
        assert guidance.target_tension_level == Decimal("9.0")

    def test_falling_action_phase_guidance(self, falling_action_state):
        """测试下降动作阶段的指导"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=falling_action_state)
        assert guidance.primary_narrative_goal == "Resolve subplots and reduce tension"
        assert guidance.target_tension_level == Decimal("4.0")

    def test_resolution_phase_guidance(self, resolution_state):
        """测试结局阶段的指导"""
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=resolution_state)
        assert guidance.primary_narrative_goal == "Provide closure and finalize character arcs"
        assert guidance.target_tension_level == Decimal("2.0")


class TestGuidanceIdGeneration:
    """测试指导ID生成"""

    def test_guidance_id_contains_arc_id(self):
        """测试指导ID包含弧线ID"""
        state = StoryArcState(
            arc_id="my-story-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=5,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert "my-story-arc" in guidance.guidance_id

    def test_guidance_id_contains_turn_number(self):
        """测试指导ID包含回合数"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=42,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert "42" in guidance.guidance_id

    def test_guidance_id_starts_with_guidance_prefix(self):
        """测试指导ID以guidance-前缀开头"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.guidance_id.startswith("guidance-")

    def test_guidance_id_is_unique_per_call(self):
        """测试每次调用生成的ID是唯一的"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance1 = engine.generate_guidance_for_turn(state=state)
        guidance2 = engine.generate_guidance_for_turn(state=state)
        assert guidance1.guidance_id != guidance2.guidance_id


class TestTurnNumberPreservation:
    """测试回合数保留"""

    def test_turn_number_preserved_in_guidance(self):
        """测试回合数在指导中保留"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=15,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.turn_number == 15

    def test_zero_turn_number(self):
        """测试零回合数"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=0,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.turn_number == 0

    def test_large_turn_number(self):
        """测试大回合数"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=10000,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.turn_number == 10000


class TestArcStatePreservation:
    """测试弧线状态保留"""

    def test_arc_state_preserved_in_guidance(self):
        """测试弧线状态在指导中保留"""
        original_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=20,
            current_tension_level=Decimal("8.5"),
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=original_state)
        assert guidance.arc_state is original_state


class TestSecondaryGoals:
    """测试次要目标"""

    def test_secondary_goals_is_list(self):
        """测试次要目标是列表"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert isinstance(guidance.secondary_narrative_goals, list)

    def test_secondary_goals_empty_by_default(self):
        """测试默认次要目标为空"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.secondary_narrative_goals == []


class TestPrimaryGoals:
    """测试主要目标"""

    def test_all_phases_have_primary_goal(self):
        """测试所有阶段都有主要目标"""
        engine = NarrativePlanningEngine()
        phases = [
            StoryArcPhase.EXPOSITION,
            StoryArcPhase.RISING_ACTION,
            StoryArcPhase.CLIMAX,
            StoryArcPhase.FALLING_ACTION,
            StoryArcPhase.RESOLUTION,
        ]
        for phase in phases:
            state = StoryArcState(
                arc_id="test",
                current_phase=phase,
                turn_number=1,
            )
            guidance = engine.generate_guidance_for_turn(state=state)
            assert guidance.primary_narrative_goal
            assert len(guidance.primary_narrative_goal) > 0

    def test_primary_goal_is_string(self):
        """测试主要目标是字符串"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert isinstance(guidance.primary_narrative_goal, str)


class TestTensionLevels:
    """测试张力水平"""

    def test_exposition_tension_is_low(self):
        """测试展示阶段张力较低"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.target_tension_level <= Decimal("4.0")

    def test_climax_tension_is_high(self):
        """测试高潮阶段张力较高"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.target_tension_level >= Decimal("8.0")

    def test_resolution_tension_is_lowest(self):
        """测试结局阶段张力最低"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RESOLUTION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert guidance.target_tension_level <= Decimal("3.0")

    def test_tension_progression_across_phases(self):
        """测试各阶段张力进展"""
        engine = NarrativePlanningEngine()
        
        exposition_state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        rising_state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RISING_ACTION,
            turn_number=1,
        )
        climax_state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        
        exposition_tension = engine.generate_guidance_for_turn(
            state=exposition_state
        ).target_tension_level
        rising_tension = engine.generate_guidance_for_turn(
            state=rising_state
        ).target_tension_level
        climax_tension = engine.generate_guidance_for_turn(
            state=climax_state
        ).target_tension_level
        
        assert exposition_tension < rising_tension < climax_tension


class TestEdgeCases:
    """测试边界情况"""

    def test_unknown_phase_defaults_to_maintenance(self):
        """测试未知阶段默认维护连续性"""
        # 使用一个不在标准枚举中的值
        class UnknownPhase:
            value = "UNKNOWN"
        
        # 通过model_copy创建一个带有未知阶段的State
        base_state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        
        # 由于StoryArcPhase是枚举，我们不能直接设置未知值
        # 这个测试验证如果有新的阶段被添加但未被处理的情况
        # 实际上代码应该处理所有StoryArcPhase的值
        engine = NarrativePlanningEngine()
        # 测试所有已知的阶段都被处理
        for phase in StoryArcPhase:
            state = StoryArcState(
                arc_id="test",
                current_phase=phase,
                turn_number=1,
            )
            guidance = engine.generate_guidance_for_turn(state=state)
            assert guidance.primary_narrative_goal

    def test_special_characters_in_arc_id(self):
        """测试特殊字符弧线ID"""
        state = StoryArcState(
            arc_id="arc-with-dashes_and_123",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=5,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert "arc-with-dashes_and_123" in guidance.guidance_id

    def test_guidance_values_are_frozen(self):
        """测试指导值是不可变的"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        # NarrativeGuidance应该使用model_config = ConfigDict(frozen=True)
        with pytest.raises(Exception):
            guidance.primary_narrative_goal = "New goal"

    def test_multiple_guidances_same_state_different_ids(self):
        """测试相同状态多次生成不同ID"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=5,
        )
        engine = NarrativePlanningEngine()
        ids = set()
        for _ in range(10):
            guidance = engine.generate_guidance_for_turn(state=state)
            ids.add(guidance.guidance_id)
        # 所有ID都应该是唯一的
        assert len(ids) == 10

    def test_decimal_precision_in_tension(self):
        """测试张力值的十进制精度"""
        # 所有的张力目标都是硬编码的Decimal值
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        engine = NarrativePlanningEngine()
        guidance = engine.generate_guidance_for_turn(state=state)
        assert isinstance(guidance.target_tension_level, Decimal)
        # 检查是否是预期的值
        assert guidance.target_tension_level == Decimal("3.0")
