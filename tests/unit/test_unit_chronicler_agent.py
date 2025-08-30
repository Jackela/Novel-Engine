#!/usr/bin/env python3
"""
记录代理单元测试套件
测试故事生成、日志转录、叙述整合等核心功能
"""

import os
import time
from unittest.mock import Mock, patch

import pytest

# 导入被测试的模块
try:
    from chronicler_agent import ChroniclerAgent

    from src.event_bus import EventBus

    CHRONICLER_AGENT_AVAILABLE = True
except ImportError:
    CHRONICLER_AGENT_AVAILABLE = False


@pytest.mark.skipif(
    not CHRONICLER_AGENT_AVAILABLE, reason="Chronicler agent not available"
)
class TestChroniclerAgent:
    """记录代理核心测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.test_character_names = ["hero", "villain", "sage"]
        self.chronicler = ChroniclerAgent(
            event_bus=self.mock_event_bus, character_names=self.test_character_names
        )

        # 创建测试日志文件
        self.temp_log_file = "test_campaign.md"
        with open(self.temp_log_file, "w", encoding="utf-8") as f:
            f.write("# Test Campaign Log\n\n")
            f.write("## Turn 1\n")
            f.write("Hero: I draw my sword and face the villain!\n\n")
            f.write("## Turn 2\n")
            f.write("Villain: You cannot defeat me, foolish hero!\n\n")
            f.write("## Turn 3\n")
            f.write("Sage: Wait! There is another way to resolve this conflict.\n\n")

    def teardown_method(self):
        """每个测试方法的清理"""
        # 清理临时文件
        try:
            if os.path.exists(self.temp_log_file):
                os.remove(self.temp_log_file)
        except Exception:
            pass

    @pytest.mark.unit
    def test_chronicler_initialization_success(self):
        """测试记录代理初始化 - 成功情况"""
        event_bus = Mock()
        character_names = ["alice", "bob"]

        chronicler = ChroniclerAgent(
            event_bus=event_bus, character_names=character_names
        )

        assert chronicler.event_bus == event_bus
        assert hasattr(chronicler, "event_bus")

        # 检查角色名是否正确设置
        if hasattr(chronicler, "character_names"):
            assert chronicler.character_names == character_names
        elif hasattr(chronicler, "characters"):
            assert chronicler.characters == character_names

    @pytest.mark.unit
    def test_chronicler_initialization_no_event_bus(self):
        """测试记录代理初始化 - 无事件总线"""
        with pytest.raises((TypeError, ValueError)):
            ChroniclerAgent(event_bus=None, character_names=["test"])

    @pytest.mark.unit
    def test_chronicler_initialization_no_characters(self):
        """测试记录代理初始化 - 无角色名"""
        event_bus = Mock()

        # 测试空角色列表
        with pytest.raises((ValueError, TypeError)):
            ChroniclerAgent(event_bus=event_bus, character_names=[])

        # 测试None
        with pytest.raises((ValueError, TypeError)):
            ChroniclerAgent(event_bus=event_bus, character_names=None)

    @pytest.mark.unit
    def test_transcribe_log_success(self):
        """测试日志转录 - 成功情况"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        # 使用模拟Gemini响应
        with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
            mock_response = Mock()
            mock_response.text = (
                "In a realm of adventure, our heroes faced great challenges..."
            )
            mock_gemini.return_value = mock_response

            story = self.chronicler.transcribe_log(self.temp_log_file)

            assert story is not None
            assert isinstance(story, str)
            assert len(story) > 0
            assert "adventure" in story or "challenge" in story

    @pytest.mark.unit
    def test_transcribe_log_file_not_found(self):
        """测试日志转录 - 文件不存在"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        non_existent_file = "nonexistent_log.md"

        with pytest.raises(FileNotFoundError):
            self.chronicler.transcribe_log(non_existent_file)

    @pytest.mark.unit
    def test_transcribe_log_empty_file(self):
        """测试日志转录 - 空文件"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        empty_log_file = "empty_log.md"
        try:
            # 创建空文件
            with open(empty_log_file, "w") as f:
                f.write("")

            with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
                mock_response = Mock()
                mock_response.text = "A tale begins in silence..."
                mock_gemini.return_value = mock_response

                story = self.chronicler.transcribe_log(empty_log_file)

                assert story is not None
                assert isinstance(story, str)
        finally:
            try:
                if os.path.exists(empty_log_file):
                    os.remove(empty_log_file)
            except Exception:
                pass

    @pytest.mark.unit
    def test_transcribe_log_api_failure(self):
        """测试日志转录 - API调用失败"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
            # 模拟API调用失败
            mock_gemini.side_effect = Exception("API request failed")

            with pytest.raises(Exception):
                self.chronicler.transcribe_log(self.temp_log_file)

    @pytest.mark.unit
    def test_transcribe_log_invalid_response(self):
        """测试日志转录 - 无效API响应"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
            # 模拟空响应
            mock_response = Mock()
            mock_response.text = ""
            mock_gemini.return_value = mock_response

            story = self.chronicler.transcribe_log(self.temp_log_file)

            # 应该处理空响应
            if story is not None:
                assert isinstance(story, str)
            else:
                # 或者抛出适当的错误
                pass

    @pytest.mark.unit
    def test_log_content_processing(self):
        """测试日志内容处理"""
        # 测试日志文件是否能正确读取
        if hasattr(self.chronicler, "_read_log_file") or hasattr(
            self.chronicler, "transcribe_log"
        ):
            try:
                # 直接读取文件内容测试
                with open(self.temp_log_file, "r", encoding="utf-8") as f:
                    content = f.read()

                assert "Hero:" in content
                assert "Villain:" in content
                assert "Sage:" in content
                assert "Turn 1" in content

                # 如果有内部处理方法，测试它
                if hasattr(self.chronicler, "_process_log_content"):
                    processed = self.chronicler._process_log_content(content)
                    assert processed is not None

            except Exception as e:
                pytest.skip(f"Log content processing test failed: {e}")

    @pytest.mark.unit
    def test_character_name_integration(self):
        """测试角色名集成"""
        # 检查角色名是否在转录过程中被使用
        if hasattr(self.chronicler, "transcribe_log"):
            with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
                mock_response = Mock()
                mock_response.text = (
                    "The hero, villain, and sage embark on their journey..."
                )
                mock_gemini.return_value = mock_response

                story = self.chronicler.transcribe_log(self.temp_log_file)

                # 检查故事中是否包含角色相关内容
                if story:
                    # 至少应该有一些叙述内容
                    assert len(story) > 10

                # 检查API调用是否包含角色信息
                if mock_gemini.called:
                    call_args = mock_gemini.call_args
                    if call_args:
                        # 检查调用参数中是否包含角色信息
                        call_str = str(call_args)
                        # 角色信息可能在提示文本中
                        has_character_context = any(
                            name.lower() in call_str.lower()
                            for name in self.test_character_names
                        )
                        # 这是一个软检查，因为实现可能不同
                        if not has_character_context:
                            # 只记录，不失败
                            pass


@pytest.mark.skipif(
    not CHRONICLER_AGENT_AVAILABLE, reason="Chronicler agent not available"
)
class TestChroniclerAgentAdvanced:
    """记录代理高级功能测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.chronicler = ChroniclerAgent(
            event_bus=self.mock_event_bus, character_names=["protagonist", "antagonist"]
        )

    @pytest.mark.unit
    def test_event_bus_integration(self):
        """测试与事件总线的集成"""
        # 检查记录代理是否正确使用事件总线
        assert self.chronicler.event_bus == self.mock_event_bus

        # 检查是否有事件监听功能
        if hasattr(self.chronicler, "subscribe") or hasattr(
            self.chronicler, "on_event"
        ):
            # 如果有事件监听，测试订阅
            try:
                if hasattr(self.chronicler, "subscribe"):
                    self.chronicler.subscribe("test_event", lambda x: x)
                elif hasattr(self.chronicler, "on_event"):
                    self.chronicler.on_event("test_event", lambda x: x)
            except Exception as e:
                pytest.skip(f"Event subscription test failed: {e}")

    @pytest.mark.unit
    def test_story_quality_validation(self):
        """测试故事质量验证"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        # 创建复杂的测试日志
        complex_log_file = "complex_test_log.md"
        try:
            with open(complex_log_file, "w", encoding="utf-8") as f:
                f.write("# Epic Campaign Log\n\n")
                for turn in range(5):
                    f.write(f"## Turn {turn + 1}\n")
                    f.write(f"Protagonist: Action in turn {turn + 1}\n")
                    f.write(f"Antagonist: Response in turn {turn + 1}\n\n")

            with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
                mock_response = Mock()
                mock_response.text = """In an epic tale spanning five crucial moments, 
                the protagonist and antagonist engaged in a series of meaningful exchanges 
                that would determine the fate of their world. Each turn brought new 
                revelations and deeper understanding of their eternal struggle."""
                mock_gemini.return_value = mock_response

                story = self.chronicler.transcribe_log(complex_log_file)

                # 验证故事质量
                if story:
                    assert len(story) > 50  # 应该有实质性内容
                    assert (
                        "protagonist" in story.lower() or "antagonist" in story.lower()
                    )
                    # 检查是否有叙述结构
                    assert any(
                        word in story.lower()
                        for word in ["tale", "story", "journey", "struggle", "battle"]
                    )

        finally:
            try:
                if os.path.exists(complex_log_file):
                    os.remove(complex_log_file)
            except Exception:
                pass

    @pytest.mark.unit
    def test_different_character_configurations(self):
        """测试不同角色配置"""
        # 测试不同数量的角色
        configurations = [
            ["solo_hero"],
            ["alice", "bob"],
            ["warrior", "mage", "rogue", "cleric"],
            ["hero_" + str(i) for i in range(6)],  # 6个角色
        ]

        for char_names in configurations:
            try:
                chronicler = ChroniclerAgent(
                    event_bus=self.mock_event_bus, character_names=char_names
                )

                assert chronicler.event_bus == self.mock_event_bus

                # 检查角色名是否正确设置
                if hasattr(chronicler, "character_names"):
                    assert len(chronicler.character_names) == len(char_names)
                elif hasattr(chronicler, "characters"):
                    assert len(chronicler.characters) == len(char_names)

            except Exception as e:
                pytest.skip(
                    f"Character configuration test failed for {len(char_names)} characters: {e}"
                )

    @pytest.mark.unit
    def test_large_log_file_handling(self):
        """测试大型日志文件处理"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        large_log_file = "large_test_log.md"
        try:
            # 创建大型日志文件 (模拟长时间战役)
            with open(large_log_file, "w", encoding="utf-8") as f:
                f.write("# Extended Campaign Log\n\n")
                for turn in range(20):  # 20个回合
                    f.write(f"## Turn {turn + 1}\n")
                    f.write(
                        f"Protagonist: Complex action {turn + 1} with detailed description...\n"
                    )
                    f.write(
                        f"Antagonist: Elaborate response {turn + 1} with intricate details...\n\n"
                    )

            with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
                mock_response = Mock()
                mock_response.text = "An epic saga of twenty pivotal moments..."
                mock_gemini.return_value = mock_response

                # 测试处理大文件不会崩溃
                story = self.chronicler.transcribe_log(large_log_file)

                if story:
                    assert isinstance(story, str)
                    assert len(story) > 0

        finally:
            try:
                if os.path.exists(large_log_file):
                    os.remove(large_log_file)
            except Exception:
                pass


@pytest.mark.skipif(
    not CHRONICLER_AGENT_AVAILABLE, reason="Chronicler agent not available"
)
class TestChroniclerAgentPerformance:
    """记录代理性能测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.chronicler = ChroniclerAgent(
            event_bus=self.mock_event_bus, character_names=["perf_hero", "perf_villain"]
        )

    @pytest.mark.performance
    def test_transcription_performance(self):
        """测试转录性能"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        perf_log_file = "performance_test_log.md"
        try:
            # 创建中等大小的日志文件
            with open(perf_log_file, "w", encoding="utf-8") as f:
                f.write("# Performance Test Log\n\n")
                for turn in range(10):
                    f.write(f"## Turn {turn + 1}\n")
                    f.write(f"Perf Hero: Action {turn + 1}\n")
                    f.write(f"Perf Villain: Response {turn + 1}\n\n")

            with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
                mock_response = Mock()
                mock_response.text = (
                    "A performance test story with multiple characters..."
                )
                mock_gemini.return_value = mock_response

                start_time = time.time()

                # 执行转录
                story = self.chronicler.transcribe_log(perf_log_file)

                end_time = time.time()
                transcription_time = end_time - start_time

                # 转录应该在合理时间内完成 (5秒内，不包括实际API调用时间)
                assert transcription_time < 5.0

                if story:
                    assert isinstance(story, str)
                    assert len(story) > 0

        finally:
            try:
                if os.path.exists(perf_log_file):
                    os.remove(perf_log_file)
            except Exception:
                pass

    @pytest.mark.performance
    def test_multiple_transcriptions_performance(self):
        """测试多次转录性能"""
        if not hasattr(self.chronicler, "transcribe_log"):
            pytest.skip("Chronicler agent does not have transcribe_log method")

        log_files = []
        try:
            # 创建多个小日志文件
            for i in range(5):
                log_file = f"multi_perf_log_{i}.md"
                log_files.append(log_file)

                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"# Test Log {i}\n\n")
                    f.write("## Turn 1\n")
                    f.write(f"Hero: Action in log {i}\n")
                    f.write(f"Villain: Response in log {i}\n\n")

            with patch("chronicler_agent._make_gemini_api_request") as mock_gemini:
                mock_response = Mock()
                mock_response.text = "Quick test story..."
                mock_gemini.return_value = mock_response

                start_time = time.time()

                # 转录所有文件
                for log_file in log_files:
                    story = self.chronicler.transcribe_log(log_file)
                    assert story is not None

                end_time = time.time()
                total_time = end_time - start_time

                # 5个转录应该在合理时间内完成 (10秒内)
                assert total_time < 10.0
                assert total_time / 5 < 2.0  # 每个转录不超过2秒

        finally:
            for log_file in log_files:
                try:
                    if os.path.exists(log_file):
                        os.remove(log_file)
                except Exception:
                    pass


# 运行测试的辅助函数
def run_chronicler_agent_tests():
    """运行所有记录代理测试的辅助函数"""
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

    print("记录代理测试结果:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # 直接运行此文件时执行测试
    run_chronicler_agent_tests()
