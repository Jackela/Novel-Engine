#!/usr/bin/env python3
"""
快速语法检查 - 确保关键模块可以导入而不抛出 SyntaxError
这是 pre-push 的防线，捕获那些在单元测试中未覆盖的模块
"""
import importlib
import sys


def check_syntax(module_path: str) -> tuple[bool, str]:
    """尝试导入模块，返回 (成功, 错误信息)"""
    try:
        importlib.import_module(module_path)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError in {module_path}: {e}"
    except Exception:
        # 其他错误（如依赖缺失）暂时忽略，我们只关心 SyntaxError
        return True, ""


def main() -> int:
    """检查关键模块的语法"""
    # 关键模块列表 - 包括 AI provider 等容易被遗漏的模块
    critical_modules = [
        # AI Providers (刚刚修复的 SyntaxError 就在这里)
        "src.contexts.ai.infrastructure.providers.ollama_provider",
        "src.contexts.ai.infrastructure.providers.openai_provider",
        "src.contexts.ai.domain.services.llm_provider",
        "src.contexts.ai",
        # API 模块
        "src.api.main_api_server",
        # 其他关键基础设施
        "src.infrastructure.state_store",
        "src.performance.monitoring.performance_monitoring",
    ]

    errors = []
    passed = 0

    print("🔍 Running syntax check on critical modules...")
    print()

    for module in critical_modules:
        success, error = check_syntax(module)
        if success:
            passed += 1
            print(f"  ✅ {module}")
        else:
            errors.append(error)
            print(f"  ❌ {module}")
            print(f"     {error}")

    print()
    print(f"结果: {passed}/{len(critical_modules)} 模块通过")

    if errors:
        print()
        print("❌ SyntaxError 检测到！请修复后再推送。")
        print()
        print("详细错误:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("✅ 所有模块语法检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
