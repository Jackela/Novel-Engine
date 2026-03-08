#!/usr/bin/env python3
"""
Pacing Manager Tests

测试节奏管理器的所有功能，包括节奏调整生成、
阶段特定调整等。
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.services.pacing_manager import PacingManager
from src.contexts.narratives.domain.value_objects import (
    PacingAdjustment,
    StoryArcPhase,
    StoryArcState,
)
pytestmark = pytest.mark.unit



class TestPacingManagerInitialization:
    """测试PacingManager初始化"""

    def test_pacing_manager_initialization(self):
        """测试节奏管理器正确初始化"""
        manager = PacingManager()
        assert manager is not None


class TestAdjustPacing:
    """测试节奏调整功能"""

    @pytest.fixture
    def exposition_state(self):
        """创建展示阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.3"),
            turns_in_current_phase=3,
            turn_number=5,
            current_tension_level=Decimal("3.0"),
        )

    @pytest.fixture
    def rising_action_state(self):
        """创建上升动作阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.RISING_ACTION,
            phase_progress=Decimal("0.5"),
            turns_in_current_phase=8,
            turn_number=15,
            current_tension_level=Decimal("6.0"),
        )

    @pytest.fixture
    def climax_state(self):
        """创建高潮阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.CLIMAX,
            phase_progress=Decimal("0.7"),
            turns_in_current_phase=5,
            turn_number=25,
            current_tension_level=Decimal("8.5"),
        )

    @pytest.fixture
    def falling_action_state(self):
        """创建下降动作阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.FALLING_ACTION,
            phase_progress=Decimal("0.4"),
            turns_in_current_phase=3,
            turn_number=30,
            current_tension_level=Decimal("5.0"),
        )

    @pytest.fixture
    def resolution_state(self):
        """创建结局阶段的示例状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.RESOLUTION,
            phase_progress=Decimal("0.6"),
            turns_in_current_phase=4,
            turn_number=35,
            current_tension_level=Decimal("2.0"),
        )

    def test_adjust_pacing_returns_pacing_adjustment(self, exposition_state):
        """测试调整节奏返回PacingAdjustment对象"""
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=exposition_state)
        assert isinstance(adjustment, PacingAdjustment)

    def test_adjust_pacing_exposition_phase(self, exposition_state):
        """测试展示阶段的节奏调整"""
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=exposition_state)
        assert adjustment.adjustment_id.startswith("pacing-")
        assert adjustment.turn_number == 5
        assert adjustment.intensity_modifier == Decimal("0")
        assert adjustment.speed_modifier == Decimal("1.0")
        assert "Maintain current pacing" in adjustment.adjustment_reason

    def test_adjust_pacing_rising_action_phase(self, rising_action_state):
        """测试上升动作阶段的节奏调整"""
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=rising_action_state)
        assert adjustment.adjustment_id.startswith("pacing-")
        assert adjustment.turn_number == 15
        assert adjustment.intensity_modifier == Decimal("0")
        assert adjustment.speed_modifier == Decimal("1.0")

    def test_adjust_pacing_climax_phase(self, climax_state):
        """测试高潮阶段的节奏调整"""
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=climax_state)
        assert adjustment.intensity_modifier == Decimal("2.0")
        assert adjustment.tension_target == Decimal("9.0")
        assert adjustment.speed_modifier == Decimal("1.5")
        assert "Climax phase requires faster pacing" in adjustment.adjustment_reason
        assert adjustment.triggered_by == "phase_analysis"

    def test_adjust_pacing_falling_action_phase(self, falling_action_state):
        """测试下降动作阶段的节奏调整"""
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=falling_action_state)
        assert adjustment.intensity_modifier == Decimal("0")
        assert adjustment.speed_modifier == Decimal("1.0")

    def test_adjust_pacing_resolution_phase(self, resolution_state):
        """测试结局阶段的节奏调整"""
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=resolution_state)
        assert adjustment.intensity_modifier == Decimal("-1.0")
        assert adjustment.tension_target == Decimal("2.0")
        assert adjustment.speed_modifier == Decimal("0.7")
        assert "Resolution phase requires slower pacing" in adjustment.adjustment_reason
        assert adjustment.triggered_by == "phase_analysis"


class TestAdjustmentIdGeneration:
    """测试调整ID生成"""

    def test_adjustment_id_contains_arc_id(self):
        """测试调整ID包含弧线ID"""
        state = StoryArcState(
            arc_id="my-arc-123",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=10,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert "my-arc-123" in adjustment.adjustment_id

    def test_adjustment_id_contains_turn_number(self):
        """测试调整ID包含回合数"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=42,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert "42" in adjustment.adjustment_id

    def test_adjustment_id_is_unique_per_call(self):
        """测试每次调用生成的ID是唯一的"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment1 = manager.adjust_pacing(state=state)
        adjustment2 = manager.adjust_pacing(state=state)
        assert adjustment1.adjustment_id != adjustment2.adjustment_id


class TestIntensityModifiers:
    """测试强度修改器"""

    def test_climax_intensity_modifier_positive(self):
        """测试高潮阶段强度修改器为正"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.intensity_modifier > Decimal("0")

    def test_resolution_intensity_modifier_negative(self):
        """测试结局阶段强度修改器为负"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RESOLUTION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.intensity_modifier < Decimal("0")

    def test_default_phases_intensity_modifier_zero(self):
        """测试默认阶段强度修改器为零"""
        manager = PacingManager()
        for phase in [StoryArcPhase.EXPOSITION, StoryArcPhase.RISING_ACTION, StoryArcPhase.FALLING_ACTION]:
            state = StoryArcState(
                arc_id="test",
                current_phase=phase,
                turn_number=1,
            )
            adjustment = manager.adjust_pacing(state=state)
            assert adjustment.intensity_modifier == Decimal("0")


class TestTensionTargets:
    """测试张力目标值"""

    def test_climax_tension_target_high(self):
        """测试高潮阶段张力目标值高"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.tension_target == Decimal("9.0")

    def test_resolution_tension_target_low(self):
        """测试结局阶段张力目标值低"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RESOLUTION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.tension_target == Decimal("2.0")

    def test_exposition_tension_target_uses_current(self):
        """测试展示阶段使用当前张力值"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
            current_tension_level=Decimal("4.5"),
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.tension_target == Decimal("4.5")


class TestSpeedModifiers:
    """测试速度修改器"""

    def test_climax_speed_modifier_increases(self):
        """测试高潮阶段速度修改器增加"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.speed_modifier == Decimal("1.5")
        assert adjustment.speed_modifier > Decimal("1.0")

    def test_resolution_speed_modifier_decreases(self):
        """测试结局阶段速度修改器减少"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RESOLUTION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.speed_modifier == Decimal("0.7")
        assert adjustment.speed_modifier < Decimal("1.0")

    def test_default_speed_modifier_is_one(self):
        """测试默认速度修改器为1"""
        manager = PacingManager()
        default_phases = [
            StoryArcPhase.EXPOSITION,
            StoryArcPhase.RISING_ACTION,
            StoryArcPhase.FALLING_ACTION,
        ]
        for phase in default_phases:
            state = StoryArcState(
                arc_id="test",
                current_phase=phase,
                turn_number=1,
            )
            adjustment = manager.adjust_pacing(state=state)
            assert adjustment.speed_modifier == Decimal("1.0")


class TestAdjustmentReasons:
    """测试调整原因"""

    def test_climax_adjustment_reason(self):
        """测试高潮阶段调整原因"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert "faster" in adjustment.adjustment_reason.lower()
        assert "climax" in adjustment.adjustment_reason.lower()

    def test_resolution_adjustment_reason(self):
        """测试结局阶段调整原因"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RESOLUTION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert "slower" in adjustment.adjustment_reason.lower()
        assert "resolution" in adjustment.adjustment_reason.lower()

    def test_default_adjustment_reason(self):
        """测试默认调整原因"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert "maintain" in adjustment.adjustment_reason.lower()


class TestTriggeredBy:
    """测试触发来源"""

    def test_phase_analysis_triggered_by(self):
        """测试阶段分析触发来源"""
        manager = PacingManager()
        for phase in [StoryArcPhase.CLIMAX, StoryArcPhase.RESOLUTION]:
            state = StoryArcState(
                arc_id="test",
                current_phase=phase,
                turn_number=1,
            )
            adjustment = manager.adjust_pacing(state=state)
            assert adjustment.triggered_by == "phase_analysis"

    def test_default_triggered_by(self):
        """测试默认触发来源"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.triggered_by == "default"


class TestEdgeCases:
    """测试边界情况"""

    def test_minimum_turn_number(self):
        """测试最小回合数"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=0,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.turn_number == 0
        assert adjustment.adjustment_id.endswith("-0-") or "-0-" in adjustment.adjustment_id

    def test_large_turn_number(self):
        """测试大回合数"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=999999,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert adjustment.turn_number == 999999

    def test_special_characters_in_arc_id(self):
        """测试特殊字符弧线ID"""
        state = StoryArcState(
            arc_id="arc-with-dashes_and_123",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        assert "arc-with-dashes_and_123" in adjustment.adjustment_id

    def test_decimal_precision_preserved(self):
        """测试十进制精度保留"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            turn_number=1,
            current_tension_level=Decimal("3.14159"),
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        # 张力目标应该保持精确值
        assert adjustment.tension_target == Decimal("3.14159")

    def test_multiple_adjustments_same_state_different_ids(self):
        """测试相同状态多次调整生成不同ID"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=5,
        )
        manager = PacingManager()
        ids = set()
        for _ in range(10):
            adjustment = manager.adjust_pacing(state=state)
            ids.add(adjustment.adjustment_id)
        # 所有ID都应该是唯一的
        assert len(ids) == 10

    def test_adjustment_values_are_frozen(self):
        """测试调整值是不可变的"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.CLIMAX,
            turn_number=1,
        )
        manager = PacingManager()
        adjustment = manager.adjust_pacing(state=state)
        # PacingAdjustment应该使用model_config = ConfigDict(frozen=True)
        with pytest.raises(Exception):  # 可以是 TypeError 或 ValidationError
            adjustment.intensity_modifier = Decimal("5.0")
