#!/usr/bin/env python3
"""
验证开发环境在配置错误时能够 Fail Fast

此脚本故意破坏配置,然后触发 LLM 调用,验证系统是否立即崩溃。
"""
import os
import sys
import subprocess
from pathlib import Path

def test_fail_fast():
    """测试开发环境 Fail Fast 行为"""
    print("=" * 60)
    print("Fail Fast 验证测试")
    print("=" * 60)

    # 1. 备份 .env 文件
    env_path = Path(__file__).parent.parent / '.env'
    env_backup = env_path.with_suffix('.env.backup')

    if env_path.exists():
        print(f"\n✓ 备份 .env → {env_backup}")
        env_path.rename(env_backup)
    else:
        env_backup = None
        print("\n⚠ 未找到 .env 文件")

    try:
        # 2. 设置环境为 DEVELOPMENT
        os.environ['NOVEL_ENGINE_ENV'] = 'development'
        print(f"✓ 设置环境: NOVEL_ENGINE_ENV=development")

        # 3. 移除 API 密钥
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        print(f"✓ 移除环境变量: GEMINI_API_KEY")

        # 4. 尝试运行 LLM 调用 (应该崩溃)
        print(f"\n--- 触发 LLM 调用 (期望崩溃) ---\n")

        test_code = """
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
from pathlib import Path
# 不加载 .env (已备份)
# load_dotenv(Path('.env'))

from src.event_bus import EventBus
from src.config.character_factory import CharacterFactory

event_bus = EventBus()
factory = CharacterFactory(event_bus)
detective = factory.create_character('detective_kane')

# 触发 LLM 调用
detective._call_llm("Test prompt")
"""

        result = subprocess.run(
            [sys.executable, '-c', test_code],
            capture_output=True,
            text=True,
            timeout=30
        )

        # 5. 验证结果
        print(f"\nReturn code: {result.returncode}")

        if result.returncode != 0:
            # 期望: 非零退出码 (崩溃)
            print(f"\n✅ 验证通过: 系统在配置错误时崩溃 (Fail Fast)")
            print(f"\nStderr 输出:")
            print(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)

            # 检查是否包含 CRITICAL 错误信息
            if "CRITICAL" in result.stderr and "GEMINI_API_KEY" in result.stderr:
                print(f"\n✅ 错误信息包含 CRITICAL 标记和配置提示")
                return True
            else:
                print(f"\n⚠️ 警告: 错误信息不包含预期的 CRITICAL 标记")
                return False
        else:
            # 失败: 系统没有崩溃
            print(f"\n❌ 验证失败: 系统应该崩溃但继续运行了")
            print(f"\nStdout 输出:")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)

            if "[LLM-Fallback]" in result.stdout:
                print(f"\n❌ 检测到 Fallback 响应, 说明硬化未完成")

            return False

    except subprocess.TimeoutExpired:
        print(f"\n⚠️ 测试超时 (30秒), 可能陷入死循环")
        return False

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # 6. 恢复 .env 文件
        if env_backup and env_backup.exists():
            env_backup.rename(env_path)
            print(f"\n✓ 恢复 .env 文件")

if __name__ == "__main__":
    success = test_fail_fast()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Fail Fast 验证成功")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ Fail Fast 验证失败")
        print("=" * 60)
        sys.exit(1)
