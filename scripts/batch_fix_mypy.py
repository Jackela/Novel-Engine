#!/usr/bin/env python3
"""
批量修复 MyPy 错误脚本
"""

import re
from pathlib import Path
from typing import Optional
import subprocess
import sys


def fix_untyped_defs(file_path: Path) -> tuple[int, int]:
    """
    修复函数缺少返回类型注解的问题。
    返回: (修复数量, 跳过的数量)
    """
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    # 跳过已完全类型化的文件检查
    if '# mypy: ignore-errors' in content or '# type: ignore' in content[:500]:
        return 0, 0
    
    fixes = 0
    skipped = 0
    
    # 模式1: 匹配没有返回类型的 __init__ 方法 (多行支持)
    # 匹配 def __init__(self, ...): 但没有 -> None
    init_pattern = r'^(\s*)def __init__\(([^)]*)\)(?!\s*->):'
    
    def replace_init(match: re.Match) -> str:
        nonlocal fixes
        indent = match.group(1)
        params = match.group(2)
        fixes += 1
        return f'{indent}def __init__({params}) -> None:'
    
    content = re.sub(init_pattern, replace_init, content, flags=re.MULTILINE)
    
    # 模式2: 匹配普通的无返回类型函数 (简单情况)
    # 排除: 已注解的、property、abstractmethod、overload
    # 使用负向前瞻来避免匹配已有返回类型的函数
    simple_func_pattern = r'^(\s*)def ([a-zA-Z_][a-zA-Z0-9_]*)\((?!self\s*[,)]|cls\s*[,)])([^)]*)\)(?!\s*->)(\s*:[^=])'
    
    def replace_simple_func(match: re.Match) -> str:
        nonlocal fixes
        indent = match.group(1)
        name = match.group(2)
        params = match.group(3)
        colon_suffix = match.group(4)
        fixes += 1
        return f'{indent}def {name}({params}) -> None{colon_suffix}'
    
    # 暂时跳过普通函数，只修复 __init__
    # content = re.sub(simple_func_pattern, replace_simple_func, content, flags=re.MULTILINE)
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
    
    return fixes, skipped


def fix_lowercase_any(file_path: Path) -> int:
    """
    修复小写 any 作为类型注解的问题 (any -> Any)
    """
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    # 检查是否已导入 Any
    has_any_import = 'from typing import' in content and 'Any' in content
    
    fixes = 0
    # 匹配 : any 或 -> any 作为类型注解
    # 排除字符串中的 any
    pattern = r'(:\s*|->\s*)any(?!\w)'
    
    def replace_any(match: re.Match) -> str:
        nonlocal fixes
        prefix = match.group(1)
        fixes += 1
        return f'{prefix}Any'
    
    content = re.sub(pattern, replace_any, content)
    
    # 添加 Any 导入如果需要
    if fixes > 0 and not has_any_import:
        # 查找 typing 导入行
        typing_import_match = re.search(r'^(from typing import.*)$', content, re.MULTILINE)
        if typing_import_match:
            old_import = typing_import_match.group(1)
            if 'Any' not in old_import:
                new_import = old_import.rstrip() + ', Any'
                content = content.replace(old_import, new_import)
        else:
            # 在文件开头添加导入
            lines = content.split('\n')
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_idx = i + 1
            lines.insert(import_idx, 'from typing import Any')
            content = '\n'.join(lines)
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
    
    return fixes


def add_missing_typing_imports(file_path: Path) -> int:
    """
    添加缺失的常用 typing 导入
    """
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    fixes = 0
    
    # 检查已有的导入
    has_typing_import = 'from typing import' in content
    typing_imports = []
    
    # 检查需要的类型
    if re.search(r'\bOptional\[', content) and 'Optional' not in content:
        typing_imports.append('Optional')
    if re.search(r'\bUnion\[', content) and 'Union' not in content:
        typing_imports.append('Union')
    if re.search(r'\bList\[', content) and 'List' not in content:
        typing_imports.append('List')
    if re.search(r'\bDict\[', content) and 'Dict' not in content:
        typing_imports.append('Dict')
    if re.search(r'\bAny\b', content) and 'Any' not in content:
        typing_imports.append('Any')
    
    if typing_imports and has_typing_import:
        # 更新现有导入
        import_match = re.search(r'from typing import ([^\n]+)', content)
        if import_match:
            existing = import_match.group(1)
            new_imports = existing.rstrip() + ', ' + ', '.join(typing_imports)
            content = content.replace(import_match.group(0), f'from typing import {new_imports}')
            fixes = len(typing_imports)
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
    
    return fixes


def run_mypy_check() -> int:
    """运行 mypy 检查并返回错误数量"""
    result = subprocess.run(
        ['python', '-m', 'mypy', 'src', '--show-error-codes', '--ignore-missing-imports'],
        capture_output=True,
        text=True
    )
    errors = result.stdout.count('error:')
    return errors


def get_error_distribution() -> dict:
    """获取错误分布统计"""
    result = subprocess.run(
        ['python', '-m', 'mypy', 'src', '--show-error-codes', '--ignore-missing-imports'],
        capture_output=True,
        text=True
    )
    
    distribution = {}
    for line in result.stdout.split('\n'):
        if 'error:' in line:
            # 提取错误代码
            match = re.search(r'\[([^\]]+)\]$', line)
            if match:
                code = match.group(1)
                distribution[code] = distribution.get(code, 0) + 1
    
    return distribution


def main():
    src_path = Path('src')
    
    print("=" * 60)
    print("MyPy 批量修复工具")
    print("=" * 60)
    
    # 统计修复前的错误
    print("\n📊 修复前统计...")
    before_errors = run_mypy_check()
    print(f"总错误数: {before_errors}")
    
    # 策略1: 修复 no-untyped-def (__init__ 方法)
    print("\n🔧 策略1: 修复 __init__ 方法返回类型...")
    total_init_fixes = 0
    files_fixed = 0
    
    for py_file in src_path.rglob('*.py'):
        fixes, _ = fix_untyped_defs(py_file)
        if fixes > 0:
            total_init_fixes += fixes
            files_fixed += 1
    
    print(f"  修复了 {total_init_fixes} 个 __init__ 方法 (在 {files_fixed} 个文件中)")
    
    # 策略2: 修复 any -> Any
    print("\n🔧 策略2: 修复小写 any 类型...")
    total_any_fixes = 0
    files_with_any_fixes = 0
    
    for py_file in src_path.rglob('*.py'):
        fixes = fix_lowercase_any(py_file)
        if fixes > 0:
            total_any_fixes += fixes
            files_with_any_fixes += 1
    
    print(f"  修复了 {total_any_fixes} 个 any -> Any (在 {files_with_any_fixes} 个文件中)")
    
    # 策略3: 添加缺失导入
    print("\n🔧 策略3: 添加缺失的 typing 导入...")
    total_import_fixes = 0
    files_with_import_fixes = 0
    
    for py_file in src_path.rglob('*.py'):
        fixes = add_missing_typing_imports(py_file)
        if fixes > 0:
            total_import_fixes += fixes
            files_with_import_fixes += 1
    
    print(f"  添加了 {total_import_fixes} 个缺失导入 (在 {files_with_import_fixes} 个文件中)")
    
    # 统计修复后的错误
    print("\n📊 修复后统计...")
    after_errors = run_mypy_check()
    print(f"总错误数: {after_errors}")
    print(f"修复了: {before_errors - after_errors} 个错误")
    
    # 显示错误分布
    print("\n📋 错误分布:")
    distribution = get_error_distribution()
    for code, count in sorted(distribution.items(), key=lambda x: -x[1])[:10]:
        print(f"  {code}: {count}")
    
    print("\n" + "=" * 60)
    print("修复完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
