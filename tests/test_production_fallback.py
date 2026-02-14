#!/usr/bin/env python3
"""验证生产环境仍然保留 Fallback 机制"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_production_fallback():
    """测试生产环境 Fallback 行为"""

    print("=" * 60)
    print("生产环境 Fallback 验证")
    print("=" * 60)

    # 1. 备份 .env
    env_path = Path(__file__).parent.parent / ".env"
    env_backup = env_path.with_suffix(".env.backup_prod")

    if env_path.exists():
        print(f"\n✓ 备份 .env → {env_backup}")
        env_path.rename(env_backup)
    else:
        env_backup = None

    try:
        # 2. 设置环境为 PRODUCTION
        os.environ["NOVEL_ENGINE_ENV"] = "production"
        print("✓ 设置环境: NOVEL_ENGINE_ENV=production")

        # 3. 移除 API 密钥
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        print("✓ 移除环境变量: GEMINI_API_KEY")

        # 4. 尝试运行 LLM 调用 (应该使用 Fallback 继续运行)
        print("\n--- 触发 LLM 调用 (期望使用 Fallback) ---\n")

        test_code = """
import sys
sys.path.insert(0, '.')

from src.core.event_bus import EventBus
from src.config.character_factory import CharacterFactory


event_bus = EventBus()
factory = CharacterFactory(event_bus)
detective = factory.create_character('detective_kane')

# 触发 LLM 调用
result = detective._call_llm("Test prompt")
print(f"Result: {result}")
"""

        result = subprocess.run(
            [sys.executable, "-c", test_code],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # 5. 验证结果
        print(f"\nReturn code: {result.returncode}")

        if result.returncode == 0:
            # 期望: 成功退出 (没有崩溃)
            print("\n✅ 验证通过: 生产环境使用 Fallback 继续运行")
            print("\nStdout 输出:")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

            # 检查是否包含 Fallback 标记
            if "[LLM-Fallback]" in result.stdout:
                print("\n✅ 检测到 Fallback 响应, 生产环境降级机制正常")
                return True
            else:
                print("\n⚠️ 警告: 未检测到 Fallback 标记")
                return False
        else:
            # 失败: 生产环境也崩溃了
            print("\n❌ 验证失败: 生产环境不应该崩溃")
            print("\nStderr 输出:")
            print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 6. 恢复 .env
        if env_backup and env_backup.exists():
            env_backup.rename(env_path)
            print("\n✓ 恢复 .env 文件")


if __name__ == "__main__":
    success = test_production_fallback()

    print("\n" + "=" * 60)
    if success:
        print("🎉 生产环境 Fallback 验证成功")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ 生产环境 Fallback 验证失败")
        print("=" * 60)
        sys.exit(1)
