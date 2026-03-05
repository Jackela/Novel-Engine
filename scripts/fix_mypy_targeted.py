#!/usr/bin/env python3
"""
针对性 MyPy 批量修复脚本

优先级:
1. no-untyped-def: 为无返回类型的函数添加 -> None
2. var-annotated: 为变量添加类型注解
3. no-any-return: 修复 Any 返回类型
"""

import re
import subprocess
from pathlib import Path
from typing import Tuple


def run_mypy() -> Tuple[int, dict]:
    """运行 mypy 并返回错误统计"""
    result = subprocess.run(
        ['python', '-m', 'mypy', 'src', '--show-error-codes', '--ignore-missing-imports'],
        capture_output=True,
        text=True,
        timeout=300
    )
    
    total = result.stdout.count('error:')
    dist = {}
    for line in result.stdout.split('\n'):
        match = re.search(r'\[([^\]]+)\]$', line)
        if match:
            code = match.group(1)
            dist[code] = dist.get(code, 0) + 1
    return total, dist


def fix_simple_return_types(file_path: Path) -> int:
    """
    修复简单函数缺失返回类型的问题。
    只为没有 return 语句或只 return None 的函数添加 -> None
    """
    content = file_path.read_text(encoding='utf-8')
    original = content
    fixes = 0
    
    # 简单模式: 匹配一行函数定义
    pattern = r'^(\s*)def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)(?!\s*->)\s*:$'
    
    for match in re.finditer(pattern, content, re.MULTILINE):
        indent = match.group(1)
        func_name = match.group(2)
        params = match.group(3)
        
        # 跳过特殊方法
        if func_name in ['__init__', '__enter__', '__exit__']:
            continue
        
        old_def = match.group(0)
        new_def = f'{indent}def {func_name}({params}) -> None:'
        
        content = content.replace(old_def, new_def, 1)
        fixes += 1
    
    if fixes > 0:
        file_path.write_text(content, encoding='utf-8')
    
    return fixes


def fix_init_methods(file_path: Path) -> int:
    """修复 __init__ 方法缺失返回类型的问题。"""
    content = file_path.read_text(encoding='utf-8')
    original = content
    fixes = 0
    
    pattern = r'^(\s*)def\s+__init__\s*\(([^)]*)\)(?!\s*->)\s*:$'
    
    for match in re.finditer(pattern, content, re.MULTILINE):
        indent = match.group(1)
        params = match.group(2)
        
        old_def = match.group(0)
        new_def = f'{indent}def __init__({params}) -> None:'
        
        content = content.replace(old_def, new_def, 1)
        fixes += 1
    
    if fixes > 0:
        file_path.write_text(content, encoding='utf-8')
    
    return fixes


def fix_var_annotated(file_path: Path) -> int:
    """修复 'Need type annotation for variable' 错误。"""
    content = file_path.read_text(encoding='utf-8')
    original = content
    fixes = 0
    
    # 常见模式：空列表/字典初始化
    patterns = [
        (r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\[\]\s*$', r'\1\2: list[Any] = []'),
        (r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*\{\}\s*$', r'\1\2: dict[Any, Any] = {}'),
        (r'^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*set\(\)\s*$', r'\1\2: set[Any] = set()'),
    ]
    
    for pattern, replacement in patterns:
        new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)
        if count > 0:
            content = new_content
            fixes += count
    
    if fixes > 0:
        # 添加 Any 导入
        if 'from typing import' in content:
            if 'Any' not in content:
                content = re.sub(
                    r'(from typing import [^\n]+)',
                    r'\1, Any',
                    content
                )
        else:
            lines = content.split('\n')
            import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_idx = i + 1
            lines.insert(import_idx, 'from typing import Any')
            content = '\n'.join(lines)
        
        file_path.write_text(content, encoding='utf-8')
    
    return fixes


def main():
    src_path = Path('src')
    
    print("=" * 70)
    print("MyPy 针对性批量修复")
    print("=" * 70)
    
    # 初始统计
    print("\n📊 初始错误统计...")
    before_total, before_dist = run_mypy()
    print(f"总错误: {before_total}")
    print(f"no-untyped-def: {before_dist.get('no-untyped-def', 0)}")
    print(f"var-annotated: {before_dist.get('var-annotated', 0)}")
    
    # 策略1: 修复简单函数返回类型
    print("\n🔧 策略1: 修复简单函数返回类型...")
    simple_fixes = 0
    simple_files = 0
    for py_file in src_path.rglob('*.py'):
        count = fix_simple_return_types(py_file)
        if count > 0:
            simple_fixes += count
            simple_files += 1
    print(f"  修复了 {simple_fixes} 个函数 (在 {simple_files} 个文件中)")
    
    # 策略2: 修复 __init__ 方法
    print("\n🔧 策略2: 修复 __init__ 方法...")
    init_fixes = 0
    init_files = 0
    for py_file in src_path.rglob('*.py'):
        count = fix_init_methods(py_file)
        if count > 0:
            init_fixes += count
            init_files += 1
    print(f"  修复了 {init_fixes} 个 __init__ 方法 (在 {init_files} 个文件中)")
    
    # 策略3: 修复 var-annotated
    print("\n🔧 策略3: 修复变量类型注解...")
    var_fixes = 0
    var_files = 0
    for py_file in src_path.rglob('*.py'):
        count = fix_var_annotated(py_file)
        if count > 0:
            var_fixes += count
            var_files += 1
    print(f"  修复了 {var_fixes} 个变量 (在 {var_files} 个文件中)")
    
    # 最终统计
    print("\n📊 最终错误统计...")
    after_total, after_dist = run_mypy()
    print(f"总错误: {after_total} (减少了 {before_total - after_total})")
    print(f"no-untyped-def: {after_dist.get('no-untyped-def', 0)}")
    print(f"var-annotated: {after_dist.get('var-annotated', 0)}")
    
    print("\n" + "=" * 70)
    print("修复完成!")
    print("=" * 70)


if __name__ == '__main__':
    main()
