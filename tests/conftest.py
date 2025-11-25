#!/usr/bin/env python3
"""
pytest配置文件和共享fixture
提供测试环境的通用设置和数据
"""

import asyncio
import importlib.util
import os
import shutil
import sys
import tempfile
import threading
from multiprocessing import active_children
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Explicitly enable async plugin because autoload is disabled via sitecustomize.
try:
    import pytest_asyncio  # noqa: F401

    pytest_plugins = ("pytest_asyncio",)
except ImportError:  # pragma: no cover
    pytest_plugins = tuple()


def pytest_configure(config):
    """Configure pytest-asyncio mode."""
    # Set asyncio_mode to auto via _ini_config before tests are collected
    # This approach works with pytest-asyncio 0.21+
    config.addinivalue_line("asyncio_mode", "auto")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path():
    """项目根目录路径"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_gemini_api_key():
    """模拟Gemini API密钥"""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key_12345"}):
        yield "test_key_12345"


@pytest.fixture
def mock_config():
    """模拟配置对象"""
    config = Mock()
    config.simulation.turns = 3
    config.gemini.api_key = "test_key"
    config.gemini.model = "gemini-1.5-flash"
    config.story.max_length = 1000
    return config


@pytest.fixture
def sample_character_data():
    """示例角色数据"""
    return {
        "name": "Test Warrior",
        "background_summary": "A brave warrior from the distant lands",
        "personality_traits": "Courageous, loyal, determined",
        "current_status": "Ready for adventure",
        "narrative_context": "Seeking glory in battle",
        "skills": {"combat": 0.8, "leadership": 0.6},
        "relationships": {"ally_1": 0.7, "rival_1": -0.3},
        "current_location": "Training Grounds",
        "inventory": ["sword", "shield", "health_potion"],
        "metadata": {"level": 5, "experience": 150},
    }


@pytest.fixture
def mock_event_bus():
    """模拟事件总线"""
    event_bus = Mock()
    event_bus.subscribe = Mock()
    event_bus.publish = Mock()
    event_bus.unsubscribe = Mock()
    return event_bus


@pytest.fixture
def mock_character_factory():
    """模拟角色工厂"""
    factory = Mock()
    factory.create_character = Mock()
    return factory


@pytest.fixture
def mock_director_agent():
    """模拟导演代理"""
    director = Mock()
    director.register_agent = Mock()
    director.run_turn = Mock()
    return director


@pytest.fixture
def mock_chronicler_agent():
    """模拟记录代理"""
    chronicler = Mock()
    chronicler.transcribe_log = Mock(return_value="Test story generated")
    return chronicler


@pytest.fixture
def sample_api_response():
    """示例API响应数据"""
    return {
        "message": "StoryForge AI Interactive Story Engine is running!",
        "status": "healthy",
        "timestamp": "2025-08-19T20:00:00",
        "version": "1.0.0",
    }


@pytest.fixture
def sample_characters_response():
    """示例角色列表响应"""
    return {"characters": ["engineer", "pilot", "scientist", "test"]}


@pytest.fixture
def sample_simulation_request():
    """示例模拟请求数据"""
    return {"character_names": ["engineer", "pilot"], "turns": 3}


@pytest.fixture
def sample_simulation_response():
    """示例模拟响应数据"""
    return {
        "story": "In a galaxy far away, the engineer and pilot worked together...",
        "participants": ["engineer", "pilot"],
        "turns_executed": 3,
        "duration_seconds": 12.5,
    }


@pytest.fixture
def mock_gemini_response():
    """模拟Gemini API响应"""
    response = Mock()
    response.text = "This is a generated story response from Gemini."
    return response


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def clean_environment(request):
    """每个测试后清理环境"""
    # 测试前设置
    original_env = os.environ.copy()
    # Provide sane defaults to ensure security middleware and docs behave predictably
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("ENABLE_RATE_LIMITING", "true")
    os.environ.setdefault("ENABLE_DOCS", "true")
    os.environ.setdefault("NOVEL_ENGINE_AGENT_VALIDATION_MODE", "strict")

    if (
        "test_director_agent_advanced" in request.node.nodeid
        or "test_director_agent_comprehensive" in request.node.nodeid
    ):
        os.environ["NOVEL_ENGINE_AGENT_VALIDATION_MODE"] = "lenient"

    yield

    # 测试后清理
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def characters_directory(temp_dir):
    """创建临时的角色目录结构"""
    chars_dir = temp_dir / "characters"
    chars_dir.mkdir()

    # 创建测试角色目录
    for char_name in ["engineer", "pilot", "scientist", "test"]:
        char_dir = chars_dir / char_name
        char_dir.mkdir()

        # 创建角色文件
        (char_dir / f"character_{char_name}.md").write_text(
            f"# {char_name.title()}\n\nA test character for testing purposes."
        )
        (char_dir / "stats.yaml").write_text(
            f"name: {char_name}\nhealth: 100\nlevel: 1"
        )

    return chars_dir


# 测试标记辅助函数
def pytest_configure(config):
    """pytest配置钩子"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "api: API测试")
    config.addinivalue_line("markers", "performance: 性能测试")
    config.addinivalue_line("markers", "security: 安全测试")
    config.addinivalue_line("markers", "slow: 慢速测试")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集行为"""
    for item in items:
        # 为API测试添加标记
        if "api" in item.nodeid:
            item.add_marker(pytest.mark.api)

        # 为慢速测试添加标记
        if item.get_closest_marker("slow"):
            item.add_marker(pytest.mark.slow)


# 测试报告钩子（仅在 pytest-html 可用时注册，避免 GA 缺失插件导致失败）
if (
    importlib.util.find_spec("pytest_html") is not None
    and os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1"
):

    def pytest_html_report_title(report):
        """自定义HTML报告标题"""
        report.title = "StoryForge AI 测试报告"


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """尽最大努力确保测试会话结束时清理所有存活资源，避免挂起。

    - 终止/回收 multiprocessing 子进程
    - 尝试取消仍在运行的 asyncio 任务
    - 等待非守护线程短暂退出
    """
    # Join non-daemon threads to avoid interpreter hang
    try:
        for t in list(threading.enumerate()):
            if t is threading.current_thread():
                continue
            # Skip daemons; they won't block interpreter exit
            if getattr(t, "daemon", False):
                continue
            t.join(timeout=1.0)
    except Exception:
        pass

    # Terminate any active multiprocessing children
    try:
        for p in active_children():
            try:
                p.terminate()
            except Exception:
                pass
            try:
                p.join(timeout=2.0)
            except Exception:
                pass
    except Exception:
        pass

    # Best-effort cancellation of pending asyncio tasks on a running loop
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
    except Exception:
        # If loop is closed or unavailable, ignore
        pass
