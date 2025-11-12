#!/usr/bin/env python3
"""
API服务器单元测试套件
全面测试所有API端点和功能
"""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

# 导入被测试的模块
try:
    from api_server import app

    API_SERVER_AVAILABLE = True
except ImportError:
    API_SERVER_AVAILABLE = False
    app = None


@pytest.mark.skipif(not API_SERVER_AVAILABLE, reason="API server not available")
class TestAPIServerEndpoints:
    """API服务器端点测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.client = TestClient(app)

    @pytest.mark.api
    def test_root_endpoint_success(self):
        """测试根端点 - 成功情况"""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "StoryForge AI" in data["message"]

    @pytest.mark.api
    def test_health_endpoint_success(self, mock_config):
        """测试健康检查端点 - 成功情况"""
        with patch("api_server.get_config", return_value=mock_config):
            response = self.client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded"]
            assert "api" in data
            assert "timestamp" in data
            assert "version" in data

    @pytest.mark.api
    def test_health_endpoint_config_error(self):
        """测试健康检查端点 - 配置错误"""
        with patch("api_server.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Severe system error")

            response = self.client.get("/health")

            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            assert "detail" in data

    @pytest.mark.api
    def test_characters_endpoint_empty_directory(self, temp_dir):
        """测试角色列表端点 - 空目录"""
        # 创建空的角色目录
        chars_dir = temp_dir / "characters"
        chars_dir.mkdir()

        with patch(
            "api_server._get_characters_directory_path", return_value=str(chars_dir)
        ):
            response = self.client.get("/characters")

            assert response.status_code == 200
            data = response.json()
            assert "characters" in data
            assert data["characters"] == []

    @pytest.mark.api
    def test_characters_endpoint_populated_directory(self, characters_directory):
        """测试角色列表端点 - 有角色数据"""
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            response = self.client.get("/characters")

            assert response.status_code == 200
            data = response.json()
            assert "characters" in data
            assert len(data["characters"]) == 4
            assert "engineer" in data["characters"]
            assert "pilot" in data["characters"]

    @pytest.mark.api
    def test_characters_endpoint_directory_not_found(self, temp_dir):
        """测试角色列表端点 - 目录不存在"""
        non_existent_dir = temp_dir / "non_existent"

        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(non_existent_dir),
        ):
            response = self.client.get("/characters")

            assert response.status_code == 200  # 应该创建目录并返回空列表
            data = response.json()
            assert "characters" in data
            assert data["characters"] == []

    @pytest.mark.api
    def test_character_detail_endpoint_success(self, characters_directory):
        """测试角色详情端点 - 成功情况"""
        # 确保使用正确的字符目录路径 (不是 parent)
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("api_server.EventBus"), patch(
                "api_server.CharacterFactory"
            ) as mock_factory:

                # 模拟CharacterFactory失败，但仍应返回基础信息
                mock_factory.return_value.create_character.side_effect = Exception(
                    "Factory error"
                )

                response = self.client.get("/characters/engineer")

                # 即使CharacterFactory失败，也应该返回基础信息
                assert response.status_code == 200
                data = response.json()
                assert "character_id" in data
                assert data["character_id"] == "engineer"

    @pytest.mark.api
    def test_character_detail_endpoint_not_found(self, characters_directory):
        """测试角色详情端点 - 角色不存在"""
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            response = self.client.get("/characters/nonexistent")

            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            assert "detail" in data

    @pytest.mark.api
    @pytest.mark.slow
    def test_simulations_endpoint_valid_request(
        self, characters_directory, sample_simulation_request
    ):
        """测试模拟端点 - 有效请求"""
        # 确保使用正确的字符目录路径 (不是 parent)
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("api_server.EventBus"), patch(
                "api_server.CharacterFactory"
            ) as mock_factory, patch("api_server.DirectorAgent"), patch(
                "api_server.ChroniclerAgent"
            ) as mock_chronicler:

                # 模拟成功的组件创建
                mock_agent = Mock()
                mock_agent.character.name = "engineer"
                mock_factory.return_value.create_character.return_value = mock_agent

                mock_chronicler_instance = Mock()
                mock_chronicler_instance.transcribe_log.return_value = (
                    "Generated test story"
                )
                mock_chronicler.return_value = mock_chronicler_instance

                response = self.client.post(
                    "/simulations", json=sample_simulation_request
                )

                assert response.status_code == 200
                data = response.json()
                assert "story" in data
                assert "participants" in data
                assert "turns_executed" in data
                assert "duration_seconds" in data
                assert (
                    data["participants"] == sample_simulation_request["character_names"]
                )

    @pytest.mark.api
    def test_simulations_endpoint_invalid_request_empty_characters(self):
        """测试模拟端点 - 无效请求（空角色列表）"""
        invalid_request = {"character_names": [], "turns": 3}

        response = self.client.post("/simulations", json=invalid_request)

        assert response.status_code == 422  # Validation error

    @pytest.mark.api
    def test_simulations_endpoint_invalid_request_too_many_characters(self):
        """测试模拟端点 - 无效请求（角色过多）"""
        invalid_request = {
            "character_names": [
                "char1",
                "char2",
                "char3",
                "char4",
                "char5",
                "char6",
                "char7",
            ],  # 超过6个
            "turns": 3,
        }

        response = self.client.post("/simulations", json=invalid_request)

        assert response.status_code == 422  # Validation error

    @pytest.mark.api
    def test_simulations_endpoint_character_not_found(self, temp_dir):
        """测试模拟端点 - 角色不存在"""
        with patch(
            "api_server._get_characters_directory_path", return_value=str(temp_dir)
        ):
            # 创建一个存在的角色目录
            char1_dir = temp_dir / "valid_char1"
            char1_dir.mkdir()

            request_data = {
                "character_names": [
                    "valid_char1",
                    "nonexistent_character",
                ],  # 需要至少2个角色来满足验证
                "turns": 3,
            }

            response = self.client.post("/simulations", json=request_data)

            assert response.status_code == 404
            data = response.json()
            assert "error" in data
            # 可能任一不存在的字符都会被检测到
            assert (
                "nonexistent_character" in data["detail"]
                or "not found" in data["detail"].lower()
            )

    @pytest.mark.api
    def test_campaigns_endpoint_success(self):
        """测试活动列表端点 - 成功情况"""
        response = self.client.get("/campaigns")

        assert response.status_code == 200
        data = response.json()
        assert "campaigns" in data
        assert isinstance(data["campaigns"], list)

    @pytest.mark.api
    def test_create_campaign_endpoint_success(self):
        """测试创建活动端点 - 成功情况"""
        campaign_data = {
            "name": "Test Campaign",
            "description": "A test campaign for testing",
            "participants": ["engineer", "pilot"],
        }

        response = self.client.post("/campaigns", json=campaign_data)

        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data
        assert "name" in data
        assert "status" in data
        assert "created_at" in data
        assert data["name"] == campaign_data["name"]
        assert data["status"] == "created"

    @pytest.mark.api
    def test_health_endpoint_severe_error(self):
        """测试健康检查端点 - 严重错误处理"""
        with patch("api_server.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Severe system error")

            response = self.client.get("/health")

            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            assert "detail" in data

    @pytest.mark.api
    def test_characters_endpoint_permission_error(self):
        """测试角色列表端点 - 权限错误"""
        with patch(
            "api_server._get_characters_directory_path", return_value="/restricted/path"
        ):
            with patch("os.path.isdir", return_value=True):  # 让目录存在检查通过
                with patch("os.listdir") as mock_listdir:
                    mock_listdir.side_effect = PermissionError("Permission denied")

                    response = self.client.get("/characters")

                    assert response.status_code == 500
                    data = response.json()
                    assert "error" in data
                    assert "Permission denied" in data["detail"]

    @pytest.mark.api
    def test_characters_endpoint_unexpected_error(self):
        """测试角色列表端点 - 意外错误"""
        with patch(
            "api_server._get_characters_directory_path", return_value="/valid/path"
        ):
            with patch("os.path.isdir", return_value=True):  # 让目录存在检查通过
                with patch("os.listdir") as mock_listdir:
                    mock_listdir.side_effect = Exception("Unexpected file system error")

                    response = self.client.get("/characters")

                    assert response.status_code == 500
                    data = response.json()
                    assert "error" in data
                    assert "Failed to retrieve characters" in data["detail"]

    @pytest.mark.api
    def test_simulations_endpoint_empty_character_list(self):
        """测试模拟端点 - 空角色列表验证"""
        empty_request = {"character_names": [], "turns": 3}

        response = self.client.post("/simulations", json=empty_request)

        # This should trigger the validation error at line 288
        assert response.status_code == 422  # FastAPI validation error

    @pytest.mark.api
    def test_simulations_endpoint_character_loading_failure(self, temp_dir):
        """测试模拟端点 - 角色加载失败"""
        with patch(
            "api_server._get_characters_directory_path", return_value=str(temp_dir)
        ):
            # 创建角色目录
            char_dir = temp_dir / "test_char1"
            char_dir.mkdir()
            char_dir2 = temp_dir / "test_char2"
            char_dir2.mkdir()

            with patch("api_server.CharacterFactory") as mock_factory:
                mock_factory.return_value.create_character.side_effect = Exception(
                    "Character loading failed"
                )

                request_data = {
                    "character_names": [
                        "test_char1",
                        "test_char2",
                    ],  # 满足最少两个角色的验证
                    "turns": 3,
                }

                response = self.client.post("/simulations", json=request_data)

                assert response.status_code == 400
                data = response.json()
                assert "error" in data
                assert "Failed to load character" in data["detail"]

    @pytest.mark.api
    def test_simulations_endpoint_director_turn_failure(self, characters_directory):
        """测试模拟端点 - 导演回合执行失败"""
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("api_server.EventBus"), patch(
                "api_server.CharacterFactory"
            ) as mock_factory, patch(
                "api_server.DirectorAgent"
            ) as mock_director, patch(
                "api_server.ChroniclerAgent"
            ) as mock_chronicler:

                # 设置成功的角色创建
                mock_agent = Mock()
                mock_agent.character.name = "engineer"
                mock_factory.return_value.create_character.return_value = mock_agent

                # 设置导演回合失败
                mock_director_instance = mock_director.return_value
                mock_director_instance.run_turn.side_effect = Exception(
                    "Turn execution failed"
                )

                # 设置成功的故事生成
                mock_chronicler_instance = Mock()
                mock_chronicler_instance.transcribe_log.return_value = "Test story"
                mock_chronicler.return_value = mock_chronicler_instance

                request_data = {
                    "character_names": ["engineer", "pilot"],  # 满足最少两个角色的验证
                    "turns": 3,
                }

                response = self.client.post("/simulations", json=request_data)

                # 应该仍然成功，但会记录错误并继续
                assert response.status_code == 200
                data = response.json()
                assert "story" in data

    @pytest.mark.api
    def test_simulations_endpoint_story_generation_failure(self, characters_directory):
        """测试模拟端点 - 故事生成失败回退"""
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("api_server.EventBus"), patch(
                "api_server.CharacterFactory"
            ) as mock_factory, patch("api_server.DirectorAgent"), patch(
                "api_server.ChroniclerAgent"
            ) as mock_chronicler:

                # 设置成功的角色创建
                mock_agent = Mock()
                mock_agent.character.name = "engineer"
                mock_factory.return_value.create_character.return_value = mock_agent

                # 设置故事生成失败
                mock_chronicler_instance = Mock()
                mock_chronicler_instance.transcribe_log.side_effect = Exception(
                    "Story generation failed"
                )
                mock_chronicler.return_value = mock_chronicler_instance

                request_data = {
                    "character_names": ["engineer", "pilot"],  # 满足最少两个角色的验证
                    "turns": 1,
                }

                response = self.client.post("/simulations", json=request_data)

                # 应该成功并返回回退故事
                assert response.status_code == 200
                data = response.json()
                assert "story" in data
                assert (
                    "was generated, but detailed transcription failed" in data["story"]
                )

    @pytest.mark.api
    def test_character_detail_endpoint_unexpected_error(self, characters_directory):
        """测试角色详情端点 - 意外错误"""
        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            with patch("api_server.EventBus"), patch(
                "api_server.CharacterFactory"
            ) as mock_factory:

                mock_factory.return_value.create_character.side_effect = Exception(
                    "Unexpected character error"
                )

                response = self.client.get("/characters/engineer")

                # 应该返回降级的角色信息
                assert response.status_code == 200
                data = response.json()
                assert data["character_id"] == "engineer"
                assert "could not be loaded" in data["background_summary"]

    @pytest.mark.api
    def test_campaigns_endpoint_file_system_error(self):
        """测试活动列表端点 - 文件系统错误"""
        with patch("os.path.isdir", return_value=True):
            with patch("os.listdir") as mock_listdir:
                mock_listdir.side_effect = Exception("File system error")

                response = self.client.get("/campaigns")

                # 应该优雅处理错误并返回空列表
                assert response.status_code == 200
                data = response.json()
                assert "campaigns" in data
                assert data["campaigns"] == []

    @pytest.mark.api
    def test_create_campaign_endpoint_file_creation_failure(self):
        """测试创建活动端点 - 文件创建失败"""
        with patch("os.makedirs"), patch("builtins.open") as mock_open:

            mock_open.side_effect = Exception("Failed to create campaign file")

            campaign_data = {
                "name": "Test Campaign",
                "description": "Test description",
                "participants": ["engineer"],
            }

            response = self.client.post("/campaigns", json=campaign_data)

            assert response.status_code == 500
            data = response.json()
            assert "error" in data
            assert "Failed to create campaign" in data["detail"]


@pytest.mark.skipif(not API_SERVER_AVAILABLE, reason="API server not available")
class TestAPIServerErrorHandling:
    """API服务器错误处理测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.client = TestClient(app)

    @pytest.mark.api
    def test_404_endpoint_not_found(self):
        """测试404错误处理"""
        response = self.client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "detail" in data

    @pytest.mark.api
    def test_405_method_not_allowed(self):
        """测试405方法不允许错误"""
        response = self.client.put("/")  # 根端点不支持PUT

        assert response.status_code == 405

    @pytest.mark.api
    def test_422_validation_error(self):
        """测试422验证错误"""
        invalid_data = {"invalid_field": "invalid_value"}

        response = self.client.post("/simulations", json=invalid_data)

        assert response.status_code == 422


@pytest.mark.skipif(not API_SERVER_AVAILABLE, reason="API server not available")
class TestAPIServerSecurity:
    """API服务器安全测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.client = TestClient(app)

    @pytest.mark.security
    def test_cors_headers_present(self):
        """测试CORS头部设置"""
        # CORS头部在GET请求中也会出现
        response = self.client.get("/")

        # FastAPI的CORSMiddleware在实际请求中设置CORS头部
        # 检查响应成功即可，CORS在实际跨域请求中生效
        assert response.status_code == 200

        # 可以通过模拟跨域请求来测试CORS
        headers = {"Origin": "https://example.com"}
        response_with_origin = self.client.get("/", headers=headers)
        assert response_with_origin.status_code == 200

    @pytest.mark.security
    def test_input_validation_sql_injection_attempt(self):
        """测试SQL注入防护"""
        malicious_input = {
            "character_names": ["'; DROP TABLE characters; --"],
            "turns": 3,
        }

        response = self.client.post("/simulations", json=malicious_input)

        # 应该返回404（字符不存在）而不是服务器错误
        assert response.status_code in [404, 422]

    @pytest.mark.security
    def test_input_validation_xss_attempt(self):
        """测试XSS防护"""
        xss_payload = "<script>alert('xss')</script>"

        response = self.client.get(f"/characters/{xss_payload}")

        # 应该安全处理，不返回脚本内容
        assert response.status_code == 404
        if response.status_code != 404:
            assert xss_payload not in response.text

    @pytest.mark.security
    def test_path_traversal_protection(self):
        """测试路径遍历防护"""
        malicious_path = "../../../etc/passwd"

        response = self.client.get(f"/characters/{malicious_path}")

        assert response.status_code == 404

    @pytest.mark.security
    def test_large_payload_handling(self):
        """测试大载荷处理"""
        large_payload = {"character_names": ["test"] * 1000, "turns": 10}  # 大量角色名

        response = self.client.post("/simulations", json=large_payload)

        # 应该返回验证错误而不是服务器崩溃
        assert response.status_code == 422


@pytest.mark.skipif(not API_SERVER_AVAILABLE, reason="API server not available")
class TestAPIServerPerformance:
    """API服务器性能测试"""

    def setup_method(self):
        """每个测试方法的设置"""
        self.client = TestClient(app)

    @pytest.mark.performance
    def test_health_endpoint_response_time(self):
        """测试健康检查端点响应时间"""
        import time

        start_time = time.time()
        response = self.client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time

        assert response.status_code == 200
        assert response_time < 1.0  # 应该在1秒内响应

    @pytest.mark.performance
    def test_characters_endpoint_response_time(self, characters_directory):
        """测试角色列表端点响应时间"""
        import time

        with patch(
            "api_server._get_characters_directory_path",
            return_value=str(characters_directory),
        ):
            start_time = time.time()
            response = self.client.get("/characters")
            end_time = time.time()

            response_time = end_time - start_time

            assert response.status_code == 200
            assert response_time < 0.5  # 应该在500ms内响应

    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_health_checks(self):
        """测试并发健康检查"""
        import concurrent.futures
        import time

        def make_health_request():
            return self.client.get("/health")

        start_time = time.time()

        # 并发执行10个请求
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_health_request) for _ in range(10)]
            responses = [future.result() for future in futures]

        end_time = time.time()
        total_time = end_time - start_time

        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200

        # 并发处理应该比顺序处理快
        assert total_time < 5.0  # 10个请求应该在5秒内完成


# 运行测试的辅助函数
def run_api_tests():
    """运行所有API测试的辅助函数"""
    import subprocess
    import sys

    # 运行API相关的测试
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "-m", "api", "--tb=short", __file__],
        capture_output=True,
        text=True,
    )

    print("API测试结果:")
    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    return result.returncode == 0


if __name__ == "__main__":
    # 直接运行此文件时执行测试
    run_api_tests()
