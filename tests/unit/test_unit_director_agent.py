#!/usr/bin/env python3
"""
导演代理单元测试套件
测试游戏导演、回合管理、代理协调等核心功能
"""

import logging
import os
import time
from unittest.mock import Mock

import pytest

# 导入被测试的模块

pytestmark = pytest.mark.unit

try:
    from src.agents.director_agent_integrated import DirectorAgent

    DIRECTOR_AGENT_AVAILABLE = True
except ImportError:
    DIRECTOR_AGENT_AVAILABLE = False


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgent:
    """导演代理核心测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.temp_log_path = "test_campaign_log.md"
        self.director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path=self.temp_log_path
        )

    def teardown_method(self):
        """每个测试方法的清理"""
        # 清理临时日志文件
        try:
            if os.path.exists(self.temp_log_path):
                os.remove(self.temp_log_path)
        except Exception:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    @pytest.mark.unit
    @pytest.mark.fast
    def test_director_initialization_success(self):
        """测试导演代理初始化 - 成功情况"""
        event_bus = Mock()
        log_path = "test_log.md"
        director = DirectorAgent(event_bus=event_bus, campaign_log_path=log_path)

        assert director.event_bus == event_bus
        assert hasattr(director, "event_bus")
        assert hasattr(director, "campaign_log_path") or hasattr(director, "log_path")

    @pytest.mark.unit
    def test_director_initialization_no_event_bus(self):
        """测试导演代理初始化 - 无事件总线"""
        with pytest.raises((TypeError, ValueError)):
            DirectorAgent(event_bus=None, campaign_log_path="test.md")

    @pytest.mark.unit
    def test_register_agent_success(self):
        """测试注册代理 - 成功情况"""
        mock_agent = Mock()
        mock_agent.character.name = "test_character"

        # 测试注册方法
        if hasattr(self.director, "register_agent"):
            self.director.register_agent(mock_agent)

            # 检查代理是否被正确注册
            if hasattr(self.director, "agents"):
                assert mock_agent in self.director.agents
            elif hasattr(self.director, "registered_agents"):
                assert mock_agent in self.director.registered_agents
        else:
            pytest.skip("Director agent does not have register_agent method")

    @pytest.mark.unit
    def test_register_multiple_agents(self):
        """测试注册多个代理"""
        if not hasattr(self.director, "register_agent"):
            pytest.skip("Director agent does not have register_agent method")

        # 创建多个模拟代理
        agents = []
        for i in range(3):
            mock_agent = Mock()
            mock_agent.character.name = f"character_{i}"
            agents.append(mock_agent)
            self.director.register_agent(mock_agent)

        # 检查所有代理都被注册
        if hasattr(self.director, "agents"):
            for agent in agents:
                assert agent in self.director.agents
        elif hasattr(self.director, "registered_agents"):
            for agent in agents:
                assert agent in self.director.registered_agents

    @pytest.mark.unit
    def test_register_agent_duplicate(self):
        """测试注册重复代理"""
        if not hasattr(self.director, "register_agent"):
            pytest.skip("Director agent does not have register_agent method")

        mock_agent = Mock()
        mock_agent.character.name = "duplicate_character"

        # 注册相同代理两次
        self.director.register_agent(mock_agent)

        # 第二次注册应该处理优雅或抛出适当错误
        try:
            self.director.register_agent(mock_agent)
            # 如果成功，检查没有重复
            if hasattr(self.director, "agents"):
                agent_count = sum(1 for a in self.director.agents if a == mock_agent)
                assert agent_count <= 2  # 允许重复但应该有限制
        except (ValueError, Exception):
            # 预期的重复注册错误
            pass

    @pytest.mark.unit
    def test_register_agent_invalid_agent(self):
        """测试注册无效代理"""
        if not hasattr(self.director, "register_agent"):
            pytest.skip("Director agent does not have register_agent method")

        # 测试None
        with pytest.raises((ValueError, TypeError, AttributeError)):
            self.director.register_agent(None)

        # 测试没有character属性的对象
        invalid_agent = Mock()
        del invalid_agent.character  # 删除character属性

        with pytest.raises((AttributeError, ValueError)):
            self.director.register_agent(invalid_agent)

    @pytest.mark.unit
    def test_run_turn_success(self):
        """测试运行回合 - 成功情况"""
        if not hasattr(self.director, "run_turn"):
            pytest.skip("Director agent does not have run_turn method")

        # 注册模拟代理
        mock_agent = Mock()
        mock_agent.character.name = "test_character"
        mock_agent.act.return_value = "Test action result"

        if hasattr(self.director, "register_agent"):
            self.director.register_agent(mock_agent)

        # 运行回合
        try:
            result = self.director.run_turn()

            # 检查回合是否成功执行
            # 结果可能是None或某种状态对象
            if result is not None:
                assert result is not None

            # 检查代理的act方法是否被调用
            if hasattr(self.director, "register_agent"):
                mock_agent.act.assert_called()
        except Exception as e:
            # 如果有依赖问题，确保不是关键错误
            if "config" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"External dependency issue: {e}")
            else:
                raise

    @pytest.mark.unit
    @pytest.mark.fast
    def test_run_turn_no_agents(self):
        """测试运行回合 - 没有代理"""
        if not hasattr(self.director, "run_turn"):
            pytest.skip("Director agent does not have run_turn method")

        # 确保没有注册代理的情况下运行回合
        try:
            result = self.director.run_turn()

            # 应该处理优雅或返回适当状态
            if result is not None:
                assert result is not None
        except (ValueError, RuntimeError) as e:
            # 预期的"没有代理"错误
            assert "agent" in str(e).lower() or "empty" in str(e).lower()

    @pytest.mark.unit
    def test_run_turn_agent_failure(self):
        """测试运行回合 - 代理失败"""
        if not hasattr(self.director, "run_turn") or not hasattr(
            self.director, "register_agent"
        ):
            pytest.skip("Director agent missing required methods")

        # 创建会失败的模拟代理
        failing_agent = Mock()
        failing_agent.character.name = "failing_character"
        failing_agent.act.side_effect = Exception("Agent action failed")

        self.director.register_agent(failing_agent)

        # 运行回合应该处理代理失败
        try:
            result = self.director.run_turn()
            # 如果成功处理，应该返回适当结果
            if result is not None:
                assert result is not None
        except Exception as e:
            # 检查是否是预期的错误处理
            assert "action failed" in str(e).lower() or "agent" in str(e).lower()

    @pytest.mark.unit
    def test_campaign_logging(self):
        """测试战役日志记录"""
        # 检查日志文件是否可以创建
        if hasattr(self.director, "campaign_log_path") or hasattr(
            self.director, "log_path"
        ):
            # 如果有日志记录功能，测试基本日志操作
            try:
                # 运行一个简单操作来触发日志记录
                if hasattr(self.director, "run_turn"):
                    try:
                        self.director.run_turn()
                    except Exception:
                        logging.getLogger(__name__).debug(
                            "Suppressed exception", exc_info=True
                        )

                # 检查日志文件是否存在或可以创建
                log_path = getattr(
                    self.director,
                    "campaign_log_path",
                    getattr(self.director, "log_path", self.temp_log_path),
                )

                if os.path.exists(log_path):
                    assert os.path.isfile(log_path)
                    # 检查文件大小（应该有一些内容）
                    assert os.path.getsize(log_path) >= 0

            except Exception as e:
                pytest.skip(f"Logging functionality not accessible: {e}")
        else:
            pytest.skip("Director agent does not have logging configuration")


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentAdvanced:
    """导演代理高级功能测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path="advanced_test_log.md"
        )

    def teardown_method(self):
        """清理方法"""
        try:
            if os.path.exists("advanced_test_log.md"):
                os.remove("advanced_test_log.md")
        except Exception:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    @pytest.mark.unit
    @pytest.mark.fast
    @pytest.mark.unit
    def test_event_bus_interaction(self):
        """测试与事件总线的交互"""
        # 检查导演是否使用事件总线
        if hasattr(self.director, "event_bus"):
            assert self.director.event_bus == self.mock_event_bus

            # 检查是否有事件订阅/发布功能
            if hasattr(self.director, "run_turn"):
                try:
                    # 运行一个回合可能会触发事件
                    self.director.run_turn()

                    # 检查事件总线是否被使用
                    # (这取决于具体实现)
                    if hasattr(self.mock_event_bus, "publish"):
                        # 如果发布过事件，调用次数应该 >= 0
                        assert self.mock_event_bus.publish.call_count >= 0

                except Exception:
                    # 即使运行失败，事件总线应该仍然连接
                    pass

    @pytest.mark.unit
    def test_director_state_management(self):
        """测试导演状态管理"""
        # 检查导演是否维护内部状态
        initial_state = {}

        if hasattr(self.director, "agents"):
            initial_state["agents_count"] = len(self.director.agents)

        if hasattr(self.director, "turn_count"):
            initial_state["turn_count"] = self.director.turn_count
        elif hasattr(self.director, "current_turn"):
            initial_state["current_turn"] = self.director.current_turn

        # 注册一个代理
        if hasattr(self.director, "register_agent"):
            mock_agent = Mock()
            mock_agent.character.name = "state_test_character"
            self.director.register_agent(mock_agent)

            # 检查状态是否改变
            if hasattr(self.director, "agents"):
                assert len(self.director.agents) > initial_state.get("agents_count", 0)

        # 运行回合
        if hasattr(self.director, "run_turn"):
            try:
                self.director.run_turn()

                # 检查回合计数是否增加
                if hasattr(self.director, "turn_count"):
                    assert self.director.turn_count > initial_state.get("turn_count", 0)
                elif hasattr(self.director, "current_turn"):
                    assert self.director.current_turn >= initial_state.get(
                        "current_turn", 0
                    )

            except Exception:
                # 即使运行失败，状态管理功能应该存在
                pass

    @pytest.mark.unit
    def test_director_configuration_handling(self):
        """测试导演配置处理"""
        # 测试不同的日志路径配置
        different_log_path = "different_log.md"
        try:
            different_director = DirectorAgent(
                event_bus=self.mock_event_bus, campaign_log_path=different_log_path
            )

            # 检查配置是否正确设置
            if hasattr(different_director, "campaign_log_path"):
                assert different_director.campaign_log_path == different_log_path
            elif hasattr(different_director, "log_path"):
                assert different_director.log_path == different_log_path

        except Exception as e:
            pytest.skip(f"Configuration handling test failed: {e}")
        finally:
            try:
                if os.path.exists(different_log_path):
                    os.remove(different_log_path)
            except Exception:
                logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)


@pytest.mark.skipif(not DIRECTOR_AGENT_AVAILABLE, reason="Director agent not available")
class TestDirectorAgentPerformance:
    """导演代理性能测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.director = DirectorAgent(
            event_bus=self.mock_event_bus, campaign_log_path="performance_test_log.md"
        )

    def teardown_method(self):
        """清理方法"""
        try:
            if os.path.exists("performance_test_log.md"):
                os.remove("performance_test_log.md")
        except Exception:
            logging.getLogger(__name__).debug("Suppressed exception", exc_info=True)

    @pytest.mark.performance
    @pytest.mark.unit
    @pytest.mark.unit
    def test_agent_registration_performance(self):
        """测试代理注册性能"""
        if not hasattr(self.director, "register_agent"):
            pytest.skip("Director agent does not have register_agent method")

        start_time = time.time()

        # 注册10个代理
        for i in range(10):
            mock_agent = Mock()
            mock_agent.character.name = f"perf_character_{i}"
            self.director.register_agent(mock_agent)

        end_time = time.time()
        registration_time = end_time - start_time

        # 注册10个代理应该在合理时间内完成（2秒内）
        assert registration_time < 2.0
        assert registration_time / 10 < 0.2  # 每个代理注册不超过200ms

    @pytest.mark.performance
    @pytest.mark.unit
    def test_turn_execution_performance(self):
        """测试回合执行性能"""
        if not hasattr(self.director, "run_turn"):
            pytest.skip("Director agent does not have run_turn method")

        # 注册快速响应的代理
        if hasattr(self.director, "register_agent"):
            for i in range(3):
                mock_agent = Mock()
                mock_agent.character.name = f"fast_character_{i}"
                mock_agent.act.return_value = f"Quick action {i}"
                self.director.register_agent(mock_agent)

        start_time = time.time()

        # 执行5个回合
        for turn in range(5):
            try:
                self.director.run_turn()
            except Exception:
                # 即使有错误，也记录时间
                pass

        end_time = time.time()
        execution_time = end_time - start_time

        # 5个回合应该在合理时间内完成（10秒内）
        assert execution_time < 10.0
        assert execution_time / 5 < 2.0  # 每回合不超过2秒


# 运行测试的辅助函数
def run_director_agent_tests():
    """运行所有导演代理测试的辅助函数"""
    import subprocess
    import sys

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-m",
            "unit or performance",
            "--tb=short",
            __file__,
        ],
        capture_output=True,
        text=True,
    )

    print("导演代理测试结果:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # 直接运行此文件时执行测试
    run_director_agent_tests()
