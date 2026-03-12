#!/usr/bin/env python3
"""
快速测试导入检查 - 确保所有测试文件可以导入而不抛出 SyntaxError
这是 pre-push 的第一道防线，比运行完整测试更快
"""
import ast
import sys
from pathlib import Path


def check_file_syntax(filepath: Path) -> tuple[bool, str]:
    """检查单个文件的语法"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
        ast.parse(source)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError in {filepath}: line {e.lineno}, col {e.offset}: {e.msg}"
    except Exception as e:
        return False, f"Error reading {filepath}: {e}"


def main() -> int:
    """检查所有测试文件的语法"""
    test_dirs = [
        Path("tests/contexts"),
        Path("tests/unit"),
        Path("tests/smoke"),
    ]
    
    errors = []
    checked = 0
    
    print("🔍 Running quick syntax check on test files...")
    print()
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
            
        for pyfile in test_dir.rglob("*.py"):
            # 只检查测试文件
            if pyfile.name.startswith("test_") or pyfile.name.endswith("_test.py"):
                checked += 1
                success, error = check_file_syntax(pyfile)
                if not success:
                    errors.append(error)
                    print(f"  ❌ {pyfile}")
                    print(f"     {error}")
    
    print()
    print(f"结果: {checked - len(errors)}/{checked} 文件通过")
    
    if errors:
        print()
        print("❌ SyntaxError 检测到！请修复后再推送。")
        print()
        print("详细错误:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    print("✅ 所有测试文件语法检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
