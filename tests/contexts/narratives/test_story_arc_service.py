#!/usr/bin/env python3
"""
Story Arc Service Tests

测试故事弧线管理器的所有功能，包括状态机转换、
阶段管理、状态验证等。
"""

from decimal import Decimal

import pytest

from src.contexts.narratives.domain.services.story_arc_manager import StoryArcManager
from src.contexts.narratives.domain.value_objects import StoryArcPhase, StoryArcState

pytestmark = pytest.mark.unit


class TestStoryArcManagerInitialization:
    """测试StoryArcManager初始化"""

    @pytest.fixture
    def valid_initial_state(self):
        """创建有效的初始状态"""
        return StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.EXPOSITION,
            phase_progress=Decimal("0.0"),
            turns_in_current_phase=0,
            turn_number=1,
            current_tension_level=Decimal("3.0"),
        )

    def test_manager_initialization_with_default_sequence(self, valid_initial_state):
        """测试使用默认序列初始化管理器"""
        manager = StoryArcManager(valid_initial_state)
        assert manager is not None
        assert manager.current_phase == StoryArcPhase.EXPOSITION

    def test_manager_default_sequence_order(self, valid_initial_state):
        """测试默认序列顺序"""
        manager = StoryArcManager(valid_initial_state)
        expected_sequence = (
            StoryArcPhase.EXPOSITION,
            StoryArcPhase.RISING_ACTION,
            StoryArcPhase.CLIMAX,
            StoryArcPhase.FALLING_ACTION,
            StoryArcPhase.RESOLUTION,
        )
        assert manager.DEFAULT_SEQUENCE == expected_sequence

    def test_manager_custom_phase_sequence(self, valid_initial_state):
        """测试自定义阶段序列"""
        custom_sequence = (
            StoryArcPhase.EXPOSITION,
            StoryArcPhase.CLIMAX,
            StoryArcPhase.RESOLUTION,
        )
        manager = StoryArcManager(valid_initial_state, phase_sequence=custom_sequence)
        assert manager.current_phase == StoryArcPhase.EXPOSITION

    def test_manager_invalid_empty_sequence(self, valid_initial_state):
        """测试空序列验证应失败 - 直接测试验证方法"""
        with pytest.raises(ValueError, match="cannot be empty"):
            StoryArcManager._validate_sequence([])

    def test_manager_invalid_duplicate_phases(self, valid_initial_state):
        """测试重复阶段初始化应失败"""
        with pytest.raises(ValueError, match="duplicate"):
            StoryArcManager(
                valid_initial_state,
                phase_sequence=(StoryArcPhase.EXPOSITION, StoryArcPhase.EXPOSITION),
            )

    def test_manager_initial_state_not_in_sequence(self, valid_initial_state):
        """测试初始状态不在序列中应失败"""
        with pytest.raises(ValueError, match="outside of the sequence"):
            StoryArcManager(
                valid_initial_state,
                phase_sequence=(StoryArcPhase.CLIMAX, StoryArcPhase.RESOLUTION),
            )


class TestCurrentStateAccess:
    """测试当前状态访问"""

    @pytest.fixture
    def manager(self):
        """创建带状态的manager"""
        state = StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.RISING_ACTION,
            phase_progress=Decimal("0.5"),
            turns_in_current_phase=5,
            turn_number=10,
            current_tension_level=Decimal("6.0"),
        )
        return StoryArcManager(state)

    def test_current_state_property(self, manager):
        """测试current_state属性"""
        state = manager.current_state
        assert isinstance(state, StoryArcState)
        assert state.arc_id == "test-arc-123"

    def test_current_phase_property(self, manager):
        """测试current_phase属性"""
        assert manager.current_phase == StoryArcPhase.RISING_ACTION

    def test_current_state_is_copy(self, manager):
        """测试current_state返回的是副本"""
        state1 = manager.current_state
        state2 = manager.current_state
        # 应该返回相同的对象，因为StoryArcState是不可变的
        assert state1 is state2


class TestCanAdvance:
    """测试阶段推进检查"""

    def test_can_advance_when_ready(self):
        """测试准备就绪时可以推进"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        assert manager.can_advance() is True

    def test_cannot_advance_when_phase_not_complete(self):
        """测试阶段未完成时不能推进"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=False,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        assert manager.can_advance() is False

    def test_cannot_advance_with_pending_requirements(self):
        """测试有待处理需求时不能推进"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=["requirement_1"],
        )
        manager = StoryArcManager(state)
        assert manager.can_advance() is False

    def test_cannot_advance_at_final_phase(self):
        """测试在最终阶段不能推进"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.RESOLUTION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        assert manager.can_advance() is False


class TestAdvanceToNextPhase:
    """测试推进到下一阶段"""

    @pytest.fixture
    def ready_manager(self):
        """创建准备就绪的manager"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
            phase_progress=Decimal("0.9"),
            turns_in_current_phase=10,
            turn_number=20,
            metadata={"key": "value"},
        )
        return StoryArcManager(state)

    def test_advance_to_next_phase_success(self, ready_manager):
        """测试成功推进到下一阶段"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.current_phase == StoryArcPhase.RISING_ACTION

    def test_advance_resets_phase_progress(self, ready_manager):
        """测试推进后重置阶段进度"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.phase_progress == Decimal("0")

    def test_advance_resets_turns_in_phase(self, ready_manager):
        """测试推进后重置当前阶段回合数"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.turns_in_current_phase == 0

    def test_advance_sets_ready_flag_false(self, ready_manager):
        """测试推进后设置准备标志为false"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.ready_for_phase_transition is False

    def test_advance_sets_next_phase(self, ready_manager):
        """测试推进后设置下一阶段"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.next_phase == StoryArcPhase.CLIMAX

    def test_advance_sets_previous_phase(self, ready_manager):
        """测试推进后设置前一阶段"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.previous_phase == StoryArcPhase.EXPOSITION

    def test_advance_preserves_arc_id(self, ready_manager):
        """测试推进后保留弧线ID"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.arc_id == "test-arc"

    def test_advance_preserves_turn_number(self, ready_manager):
        """测试推进后保留回合数"""
        new_state = ready_manager.advance_to_next_phase()
        assert new_state.turn_number == 20

    def test_advance_with_metadata_updates(self, ready_manager):
        """测试带元数据更新的推进"""
        updates = {"new_key": "new_value"}
        new_state = ready_manager.advance_to_next_phase(metadata_updates=updates)
        assert new_state.metadata.get("new_key") == "new_value"
        assert new_state.metadata.get("key") == "value"  # 保留原有值

    def test_advance_with_state_overrides(self, ready_manager):
        """测试带状态覆盖的推进"""
        overrides = {"current_tension_level": Decimal("7.0")}
        new_state = ready_manager.advance_to_next_phase(state_overrides=overrides)
        assert new_state.current_tension_level == Decimal("7.0")

    def test_advance_when_not_ready_raises_error(self):
        """测试未就绪时推进应抛出错误"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=False,
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="not marked complete"):
            manager.advance_to_next_phase()

    def test_advance_with_pending_requirements_raises_error(self):
        """测试有待处理需求时推进应抛出错误"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=["req1"],
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="requirements are still pending"):
            manager.advance_to_next_phase()

    def test_advance_at_final_phase_raises_error(self):
        """测试在最终阶段推进应抛出错误"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.RESOLUTION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="already at the final phase"):
            manager.advance_to_next_phase()

    def test_advance_with_invalid_next_phase_hint_raises_error(self):
        """测试无效的下一阶段提示应抛出错误"""
        state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
            next_phase=StoryArcPhase.CLIMAX,  # 应该是 RISING_ACTION
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="Invalid next_phase hint"):
            manager.advance_to_next_phase()


class TestUpdateState:
    """测试状态更新"""

    def test_update_state_success(self):
        """测试成功更新状态"""
        initial_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(initial_state)
        new_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.RISING_ACTION,
        )
        result = manager.update_state(new_state)
        assert result is new_state
        assert manager.current_phase == StoryArcPhase.RISING_ACTION

    def test_update_state_different_arc_id_raises_error(self):
        """测试不同弧线ID的状态更新应失败"""
        initial_state = StoryArcState(
            arc_id="test-arc-1",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(initial_state)
        new_state = StoryArcState(
            arc_id="test-arc-2",
            current_phase=StoryArcPhase.RISING_ACTION,
        )
        with pytest.raises(ValueError, match="cannot switch to a different arc_id"):
            manager.update_state(new_state)

    def test_update_state_regression_raises_error(self):
        """测试回退到早期阶段应失败"""
        initial_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.CLIMAX,
        )
        manager = StoryArcManager(initial_state)
        new_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        with pytest.raises(ValueError, match="cannot regress"):
            manager.update_state(new_state)

    def test_update_state_skip_phases_raises_error(self):
        """测试跳过阶段应失败"""
        initial_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(initial_state)
        new_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.CLIMAX,
        )
        with pytest.raises(ValueError, match="Cannot skip phases"):
            manager.update_state(new_state)


class TestPhaseSequence:
    """测试阶段序列功能"""

    def test_default_sequence_all_phases(self):
        """测试默认序列包含所有阶段"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        assert StoryArcPhase.EXPOSITION in manager.DEFAULT_SEQUENCE
        assert StoryArcPhase.RISING_ACTION in manager.DEFAULT_SEQUENCE
        assert StoryArcPhase.CLIMAX in manager.DEFAULT_SEQUENCE
        assert StoryArcPhase.FALLING_ACTION in manager.DEFAULT_SEQUENCE
        assert StoryArcPhase.RESOLUTION in manager.DEFAULT_SEQUENCE

    def test_phase_index_map_created_correctly(self):
        """测试阶段索引映射正确创建"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        assert manager._phase_index_map[StoryArcPhase.EXPOSITION] == 0
        assert manager._phase_index_map[StoryArcPhase.RISING_ACTION] == 1
        assert manager._phase_index_map[StoryArcPhase.CLIMAX] == 2
        assert manager._phase_index_map[StoryArcPhase.FALLING_ACTION] == 3
        assert manager._phase_index_map[StoryArcPhase.RESOLUTION] == 4

    def test_next_phase_calculation(self):
        """测试下一阶段计算"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        next_phase = manager._next_phase(StoryArcPhase.EXPOSITION)
        assert next_phase == StoryArcPhase.RISING_ACTION

    def test_next_phase_at_final_returns_none(self):
        """测试在最终阶段下一阶段返回None"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        next_phase = manager._next_phase(StoryArcPhase.RESOLUTION)
        assert next_phase is None

    def test_require_next_phase_success(self):
        """测试要求下一阶段成功"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        next_phase = manager._require_next_phase(StoryArcPhase.EXPOSITION)
        assert next_phase == StoryArcPhase.RISING_ACTION

    def test_require_next_phase_at_final_raises_error(self):
        """测试在最终阶段要求下一阶段应失败"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="No further phases"):
            manager._require_next_phase(StoryArcPhase.RESOLUTION)


class TestEnsureCanAdvance:
    """测试推进前检查"""

    def test_ensure_can_advance_success(self):
        """测试推进前检查成功"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        # 不应抛出异常
        manager._ensure_can_advance()

    def test_ensure_can_advance_at_final_raises(self):
        """测试在最终阶段推进前检查应失败"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RESOLUTION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="already at the final phase"):
            manager._ensure_can_advance()

    def test_ensure_can_advance_not_complete_raises(self):
        """测试阶段未完成时推进前检查应失败"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=False,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="not marked complete"):
            manager._ensure_can_advance()

    def test_ensure_can_advance_pending_requirements_raises(self):
        """测试有待处理需求时推进前检查应失败"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=["req1"],
        )
        manager = StoryArcManager(state)
        with pytest.raises(RuntimeError, match="requirements are still pending"):
            manager._ensure_can_advance()


class TestEdgeCases:
    """测试边界情况"""

    def test_manager_with_minimal_state(self):
        """测试使用最小状态初始化"""
        state = StoryArcState(
            arc_id="minimal",
            current_phase=StoryArcPhase.EXPOSITION,
        )
        manager = StoryArcManager(state)
        assert manager.current_phase == StoryArcPhase.EXPOSITION

    def test_manager_arc_id_preservation(self):
        """测试弧线ID保留"""
        state = StoryArcState(
            arc_id="test-arc-123",
            current_phase=StoryArcPhase.CLIMAX,
        )
        manager = StoryArcManager(state)
        assert manager.current_state.arc_id == "test-arc-123"

    def test_advance_multiple_phases_sequentially(self):
        """测试连续推进多个阶段"""
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state)

        # 推进到 RISING_ACTION
        state1 = manager.advance_to_next_phase()
        assert state1.current_phase == StoryArcPhase.RISING_ACTION

        # 手动设置为可推进
        state2 = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.RISING_ACTION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager.update_state(state2)

        # 推进到 CLIMAX
        state3 = manager.advance_to_next_phase()
        assert state3.current_phase == StoryArcPhase.CLIMAX

    def test_custom_sequence_shorter_than_default(self):
        """测试比默认序列短的自定义序列"""
        custom_sequence = (StoryArcPhase.EXPOSITION, StoryArcPhase.CLIMAX)
        state = StoryArcState(
            arc_id="test",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
        )
        manager = StoryArcManager(state, phase_sequence=custom_sequence)
        new_state = manager.advance_to_next_phase()
        assert new_state.current_phase == StoryArcPhase.CLIMAX
        # 现在应该在最终阶段
        assert manager.can_advance() is False

    def test_state_timestamp_updated_on_advance(self):
        """测试推进时更新时间戳"""
        from datetime import datetime, timezone

        ready_state = StoryArcState(
            arc_id="test-arc",
            current_phase=StoryArcPhase.EXPOSITION,
            ready_for_phase_transition=True,
            transition_requirements=[],
            state_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        manager = StoryArcManager(ready_state)
        _ = manager.current_state.state_timestamp
        new_state = manager.advance_to_next_phase()
        # 新的时间戳应该与旧的不同（因为是新生成的）
        assert new_state.state_timestamp is not None
        # 时间戳应该是UTC时间
        assert new_state.state_timestamp.tzinfo is not None
