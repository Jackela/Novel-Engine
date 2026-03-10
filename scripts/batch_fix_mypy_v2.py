#!/usr/bin/env python3
"""
批量修复 MyPy 错误脚本 V2
处理多种常见模式：
1. 无返回类型的函数 -> 添加 -> None
2. 无参数类型的函数 -> 添加 Any 类型（保守策略）
3. 小写 any -> 大写 Any
4. 添加缺失的 typing 导入
"""

import re
import subprocess
from pathlib import Path


def has_return_statement(content: str, func_start: int, func_end: int) -> bool:
    """检查函数体是否有 return 语句（非 None）"""
    body = content[func_start:func_end]
    # 匹配非空的 return 语句
    return bool(re.search(r"\breturn\s+[^\s#]", body))


def fix_missing_return_types(file_path: Path) -> int:
    """
    修复缺少返回类型注解的函数。
    只为没有显式 return 值的函数添加 -> None
    """
    content = file_path.read_text(encoding="utf-8")
    _original_content = content
    fixes = 0

    # 匹配模式: def name(...) : （没有 -> 返回类型）
    # 排除已注解的函数、property、装饰器后的函数
    # 使用更精确的多行匹配

    # 首先找到所有函数定义 (Note: regex pattern kept for reference, but line-by-line parsing used)
    _func_pattern = r"^(\s*)def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)(?!\s*->)(\s*:)"

    # 由于需要分析函数体，我们需要逐行处理
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        match = re.match(r"^(\s*)def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)$", line)

        if match and "->" not in line:
            indent = match.group(1)
            func_name = match.group(2)
            params_start = match.group(3)

            # 收集完整的参数列表（可能跨多行）
            params = params_start
            paren_count = params_start.count("(") - params_start.count(")")
            j = i

            while paren_count > 0 and j + 1 < len(lines):
                j += 1
                params += "\n" + lines[j]
                paren_count += lines[j].count("(") - lines[j].count(")")

            # 检查是否已经有关闭括号和冒号
            close_match = re.search(r"\)(\s*:)$", params.split("\n")[-1])

            if close_match and "->" not in params:
                # 这是一个没有返回类型的函数定义
                # 保守策略：添加 -> None
                # 替换最后一个 ) 为 ) -> None
                last_paren_idx = params.rfind(")")
                if last_paren_idx != -1:
                    suffix = close_match.group(1)
                    new_params = params[: last_paren_idx + 1] + " -> None" + suffix

                    # 重构这一行/多行
                    if "\n" in params:
                        param_lines = new_params.split("\n")
                        # 保持原始缩进
                        new_lines.append(
                            indent + "def " + func_name + "(" + param_lines[0]
                        )
                        for pl in param_lines[1:]:
                            new_lines.append(pl)
                    else:
                        new_lines.append(indent + "def " + func_name + "(" + new_params)

                    fixes += 1
                    i = j + 1
                    continue

        new_lines.append(line)
        i += 1

    if fixes > 0:
        new_content = "\n".join(new_lines)
        file_path.write_text(new_content, encoding="utf-8")

    return fixes


def fix_lowercase_any(file_path: Path) -> int:
    """
    修复小写 any 作为类型注解的问题。
    同时确保 Any 已导入。
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes = 0

    # 匹配类型注解中的小写 any
    # : any 或 -> any
    patterns = [
        (r":\s*any\b(?!\w)", ": Any"),
        (r"->\s*any\b(?!\w)", "-> Any"),
    ]

    for pattern, replacement_prefix in patterns:

        def replace_match(match):
            nonlocal fixes
            fixes += 1
            if replacement_prefix.startswith(":"):
                return ": Any"
            else:
                return "-> Any"

        content = re.sub(pattern, replace_match, content, flags=re.MULTILINE)

    # 如果需要修复且没有 Any 导入，添加导入
    if fixes > 0 and "from typing import" in content:
        # 检查是否已有 Any
        if "Any" not in content or not re.search(
            r"from typing import.*\bAny\b", content
        ):
            # 添加到现有的 typing 导入
            content = re.sub(
                r"(from typing import [^\n]+)",
                lambda m: m.group(1) + ", Any"
                if "Any" not in m.group(1)
                else m.group(1),
                content,
            )
    elif fixes > 0:
        # 添加新的 typing 导入
        content = "from typing import Any\n" + content

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")

    return fixes


def fix_dataclass_field_any(file_path: Path) -> int:
    """
    修复 dataclass 字段中的 any 类型。
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes = 0

    # 匹配 field(default=...) 中的 any
    pattern = r"(:\s*)any(\s*=\s*field\()"

    def replace_match(match):
        nonlocal fixes
        fixes += 1
        return match.group(1) + "Any" + match.group(2)

    content = re.sub(pattern, replace_match, content)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")

    return fixes


def add_missing_imports(file_path: Path) -> int:
    """
    根据代码中使用的类型添加缺失的导入。
    """
    content = file_path.read_text(encoding="utf-8")
    original_content = content
    fixes = 0

    # 检查已有的导入
    existing_imports = set()
    for match in re.finditer(r"from typing import ([^\n]+)", content):
        imports = match.group(1).split(",")
        existing_imports.update(i.strip() for i in imports)

    # 检查需要的类型
    needed_types = []

    # 检查各种类型注解的使用
    type_checks = [
        (r"\bOptional\[", "Optional"),
        (r"\bUnion\[", "Union"),
        (r"\bList\[", "List"),
        (r"\bDict\[", "Dict"),
        (r"\bSet\[", "Set"),
        (r"\bTuple\[", "Tuple"),
        (r"\bCallable\[", "Callable"),
        (r"\bAny\b", "Any"),
        (r"\bClassVar\[", "ClassVar"),
        (r"\bFinal\[", "Final"),
        (r"\bProtocol\b", "Protocol"),
        (r"\bTypedDict\b", "TypedDict"),
        (r"\bNamedTuple\b", "NamedTuple"),
    ]

    for pattern, type_name in type_checks:
        if re.search(pattern, content) and type_name not in existing_imports:
            if type_name not in needed_types:
                needed_types.append(type_name)

    # 添加缺失的导入
    if needed_types and "from typing import" in content:
        # 更新现有导入
        old_import_match = re.search(r"from typing import ([^\n]+)", content)
        if old_import_match:
            old_imports = old_import_match.group(1)
            new_types = [t for t in needed_types if t not in old_imports]
            if new_types:
                new_import_str = old_imports.rstrip() + ", " + ", ".join(new_types)
                content = content.replace(
                    f"from typing import {old_imports}",
                    f"from typing import {new_import_str}",
                )
                fixes = len(new_types)
    elif needed_types:
        # 添加新的导入块
        # 找到合适的插入位置（其他 import 之后）
        lines = content.split("\n")
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                insert_idx = i + 1

        lines.insert(insert_idx, f'from typing import {", ".join(needed_types)}')
        content = "\n".join(lines)
        fixes = len(needed_types)

    if content != original_content:
        file_path.write_text(content, encoding="utf-8")

    return fixes


def run_mypy() -> tuple[int, dict]:
    """运行 mypy 并返回错误数和分布"""
    result = subprocess.run(
        [
            "python",
            "-m",
            "mypy",
            "src",
            "--show-error-codes",
            "--ignore-missing-imports",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    error_count = result.stdout.count("error:")

    # 解析错误分布
    distribution = {}
    for line in result.stdout.split("\n"):
        match = re.search(r"\[([^\]]+)\]$", line)
        if match:
            code = match.group(1)
            distribution[code] = distribution.get(code, 0) + 1

    return error_count, distribution


def main():
    src_path = Path("src")

    print("=" * 70)
    print("MyPy 批量修复工具 V2")
    print("=" * 70)

    # 统计修复前
    print("\n📊 统计修复前错误...")
    before_errors, before_dist = run_mypy()
    print(f"总错误数: {before_errors}")
    print("\n前10错误类型:")
    for code, count in sorted(before_dist.items(), key=lambda x: -x[1])[:10]:
        pct = count / before_errors * 100
        print(f"  {code}: {count} ({pct:.1f}%)")

    # 策略1: 修复小写 any
    print("\n🔧 策略1: 修复小写 any -> Any...")
    any_fixes = 0
    any_files = 0
    for py_file in src_path.rglob("*.py"):
        fixes = fix_lowercase_any(py_file)
        if fixes > 0:
            any_fixes += fixes
            any_files += 1
    print(f"  修复了 {any_fixes} 处 any -> Any (在 {any_files} 个文件中)")

    # 策略2: 修复 dataclass field any
    print("\n🔧 策略2: 修复 dataclass field 中的 any...")
    field_fixes = 0
    field_files = 0
    for py_file in src_path.rglob("*.py"):
        fixes = fix_dataclass_field_any(py_file)
        if fixes > 0:
            field_fixes += fixes
            field_files += 1
    print(f"  修复了 {field_fixes} 处 field any (在 {field_files} 个文件中)")

    # 策略3: 添加缺失导入
    print("\n🔧 策略3: 添加缺失的 typing 导入...")
    import_fixes = 0
    import_files = 0
    for py_file in src_path.rglob("*.py"):
        fixes = add_missing_imports(py_file)
        if fixes > 0:
            import_fixes += fixes
            import_files += 1
    print(f"  添加了 {import_fixes} 个导入 (在 {import_files} 个文件中)")

    # 策略4: 修复缺失返回类型 (更保守，先跳过)
    print("\n🔧 策略4: 修复缺失的返回类型 (跳过 - 需要更仔细分析)...")

    # 统计修复后
    print("\n📊 统计修复后错误...")
    after_errors, after_dist = run_mypy()
    print(f"总错误数: {after_errors}")
    print(f"修复了: {before_errors - after_errors} 个错误")
    print(f"剩余需要修复: {after_errors}")

    print("\n📋 修复后错误分布 (前10):")
    for code, count in sorted(after_dist.items(), key=lambda x: -x[1])[:10]:
        pct = count / after_errors * 100 if after_errors > 0 else 0
        print(f"  {code}: {count} ({pct:.1f}%)")

    # 保存详细错误报告
    with open("mypy_errors_after_batch.txt", "w") as f:
        subprocess.run(
            [
                "python",
                "-m",
                "mypy",
                "src",
                "--show-error-codes",
                "--ignore-missing-imports",
            ],
            stdout=f,
            timeout=300,
        )
    print("\n📝 详细错误报告已保存到 mypy_errors_after_batch.txt")

    print("\n" + "=" * 70)
    print("批量修复完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
