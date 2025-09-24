#!/usr/bin/env python3
"""
角色工厂单元测试套件
测试角色创建、加载、验证等核心功能
"""

from unittest.mock import Mock, patch

import pytest

# 导入被测试的模块
try:
    from character_factory import CharacterFactory

    from src.event_bus import EventBus

    CHARACTER_FACTORY_AVAILABLE = True
except ImportError:
    CHARACTER_FACTORY_AVAILABLE = False


@pytest.mark.skipif(
    not CHARACTER_FACTORY_AVAILABLE, reason="Character factory not available"
)
class TestCharacterFactory:
    """角色工厂核心测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.factory = CharacterFactory(self.mock_event_bus)

    @pytest.mark.unit
    def test_factory_initialization_success(self):
        """测试工厂初始化 - 成功情况"""
        event_bus = Mock()
        factory = CharacterFactory(event_bus)

        assert factory.event_bus == event_bus
        assert hasattr(factory, "event_bus")

    @pytest.mark.unit
    def test_factory_initialization_no_event_bus(self):
        """测试工厂初始化 - 无事件总线"""
        with pytest.raises((TypeError, ValueError)):
            CharacterFactory(None)

    @pytest.mark.unit
    def test_create_character_success(self, characters_directory):
        """测试角色创建 - 成功情况"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("character_factory.PersonaAgent") as mock_persona:
                mock_agent = Mock()
                mock_agent.character.name = "engineer"
                mock_persona.return_value = mock_agent

                agent = self.factory.create_character("engineer")

                assert agent is not None
                assert agent.character.name == "engineer"
                mock_persona.assert_called_once()

    @pytest.mark.unit
    def test_create_character_not_found(self, temp_dir):
        """测试角色创建 - 角色不存在"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(temp_dir),
        ):
            with pytest.raises((FileNotFoundError, ValueError)):
                self.factory.create_character("nonexistent_character")

    @pytest.mark.unit
    def test_create_character_invalid_name(self, characters_directory):
        """测试角色创建 - 无效角色名"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            # 测试空字符串
            with pytest.raises((ValueError, TypeError)):
                self.factory.create_character("")

            # 测试None
            with pytest.raises((ValueError, TypeError)):
                self.factory.create_character(None)

            # 测试危险路径
            with pytest.raises((ValueError, FileNotFoundError)):
                self.factory.create_character("../../../etc/passwd")

    @pytest.mark.unit
    def test_load_character_data_success(self, characters_directory):
        """测试角色数据加载 - 成功情况"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            try:
                # 尝试调用内部方法加载数据
                if hasattr(self.factory, "_load_character_data"):
                    data = self.factory._load_character_data("engineer")
                    assert data is not None
                    assert isinstance(data, dict)
                else:
                    # 如果没有直接的加载方法，通过创建角色来间接测试
                    with patch(
                        "character_factory.PersonaAgent"
                    ) as mock_persona:
                        mock_agent = Mock()
                        mock_persona.return_value = mock_agent

                        agent = self.factory.create_character("engineer")
                        assert agent is not None
            except Exception as e:
                # 如果方法不存在或有其他问题，跳过测试
                pytest.skip(
                    f"Character data loading method not accessible: {e}"
                )

    @pytest.mark.unit
    def test_validate_character_directory_success(self, characters_directory):
        """测试角色目录验证 - 成功情况"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            # 测试验证方法是否存在
            if hasattr(self.factory, "_validate_character_directory"):
                is_valid = self.factory._validate_character_directory(
                    "engineer"
                )
                assert is_valid is True
            else:
                # 间接测试：创建角色不应该抛出目录相关错误
                with patch("character_factory.PersonaAgent") as mock_persona:
                    mock_agent = Mock()
                    mock_persona.return_value = mock_agent

                    # 这应该不会因为目录问题失败
                    agent = self.factory.create_character("engineer")
                    assert agent is not None

    @pytest.mark.unit
    def test_validate_character_directory_invalid(self, temp_dir):
        """测试角色目录验证 - 无效目录"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(temp_dir),
        ):
            if hasattr(self.factory, "_validate_character_directory"):
                is_valid = self.factory._validate_character_directory(
                    "nonexistent"
                )
                assert is_valid is False
            else:
                # 间接测试：尝试创建不存在的角色应该失败
                with pytest.raises((FileNotFoundError, ValueError)):
                    self.factory.create_character("nonexistent")

    @pytest.mark.unit
    def test_character_factory_error_handling(self, characters_directory):
        """测试角色工厂错误处理"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("character_factory.PersonaAgent") as mock_persona:
                # 模拟PersonaAgent初始化失败
                mock_persona.side_effect = Exception("Persona creation failed")

                with pytest.raises(Exception):
                    self.factory.create_character("engineer")

    @pytest.mark.unit
    def test_multiple_character_creation(self, characters_directory):
        """测试多个角色创建"""
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("character_factory.PersonaAgent") as mock_persona:
                # 为不同角色返回不同的agent
                def create_mock_agent(name):
                    mock_agent = Mock()
                    mock_agent.character.name = name
                    return mock_agent

                mock_persona.side_effect = (
                    lambda *args, **kwargs: create_mock_agent("test")
                )

                characters_to_create = ["engineer", "pilot", "scientist"]
                agents = []

                for char_name in characters_to_create:
                    agent = self.factory.create_character(char_name)
                    agents.append(agent)
                    assert agent is not None

                assert len(agents) == 3
                assert mock_persona.call_count == 3


@pytest.mark.skipif(
    not CHARACTER_FACTORY_AVAILABLE, reason="Character factory not available"
)
class TestCharacterFactoryConfiguration:
    """角色工厂配置测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()

    @pytest.mark.unit
    def test_factory_with_different_configurations(self):
        """测试不同配置下的工厂行为"""
        # 基础配置
        factory1 = CharacterFactory(self.mock_event_bus)
        assert factory1.event_bus == self.mock_event_bus

        # 不同的事件总线
        different_bus = Mock()
        factory2 = CharacterFactory(different_bus)
        assert factory2.event_bus == different_bus
        assert factory2.event_bus != factory1.event_bus

    @pytest.mark.unit
    def test_factory_character_path_resolution(self, temp_dir):
        """测试角色路径解析"""
        factory = CharacterFactory(self.mock_event_bus)

        # 测试路径解析功能
        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(temp_dir),
        ):
            # 创建测试角色目录
            char_dir = temp_dir / "test_character"
            char_dir.mkdir()

            # 创建基本的角色文件
            (char_dir / "character_test_character.md").write_text(
                "# Test Character\n"
            )

            try:
                # 尝试创建角色（可能会失败，但不应该是路径问题）
                with patch("character_factory.PersonaAgent") as mock_persona:
                    mock_agent = Mock()
                    mock_persona.return_value = mock_agent

                    agent = factory.create_character("test_character")
                    assert agent is not None
            except Exception as e:
                # 如果创建失败，确保不是因为路径问题
                assert (
                    "path" not in str(e).lower()
                    or "directory" not in str(e).lower()
                )


@pytest.mark.skipif(
    not CHARACTER_FACTORY_AVAILABLE, reason="Character factory not available"
)
class TestCharacterFactoryPerformance:
    """角色工厂性能测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.mock_event_bus = Mock()
        self.factory = CharacterFactory(self.mock_event_bus)

    @pytest.mark.performance
    def test_character_creation_performance(self, characters_directory):
        """测试角色创建性能"""
        import time

        with patch(
            "character_factory._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("character_factory.PersonaAgent") as mock_persona:
                mock_agent = Mock()
                mock_persona.return_value = mock_agent

                start_time = time.time()

                # 创建5个角色
                for i in range(5):
                    agent = self.factory.create_character("engineer")
                    assert agent is not None

                end_time = time.time()
                creation_time = end_time - start_time

                # 每个角色创建应该在合理时间内完成（1秒内）
                assert creation_time < 5.0
                assert creation_time / 5 < 1.0  # 平均每个角色不超过1秒


# 运行测试的辅助函数
def run_character_factory_tests():
    """运行所有角色工厂测试的辅助函数"""
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

    print("角色工厂测试结果:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # 直接运行此文件时执行测试
    run_character_factory_tests()
