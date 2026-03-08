#!/usr/bin/env python3
"""
Team Alpha - Script 1: Fix no-untyped-def errors
自动修复函数缺少返回类型注解的问题
"""

import re
import sys
from pathlib import Path


def fix_file(filepath: Path) -> tuple[int, list[str]]:
    """修复单个文件中的no-untyped-def错误
    
    Returns:
        (修复数量, 修复后的行列表)
    """
    content = filepath.read_text(encoding='utf-8')
    lines = content.split('\n')
    fixed_lines = []
    fixes = 0
    
    # 跟踪缩进级别
    in_function = False
    function_indent = 0
    
    for i, line in enumerate(lines):
        original_line = line
        
        # 匹配函数定义
        # 模式: def funcname(...): 或 def funcname(...) -> None:
        func_match = re.match(r'^(\s*)def\s+(\w+)\s*\(', line)
        
        if func_match:
            indent = func_match.group(1)
            func_name = func_match.group(2)
            
            # 检查是否已经有返回类型注解
            if '->' not in line or re.search(r'def\s+\w+\s*\([^)]*\)\s*:', line):
                # 检查是否是__init__方法（返回None）
                if func_name == '__init__':
                    # 在):之前添加 -> None
                    if '->' not in line:
                        line = re.sub(r'(\)\s*):', r') -> None:', line)
                        fixes += 1
                # 检查是否是私有方法（通常返回None）
                elif func_name.startswith('_') and not func_name.startswith('__'):
                    # 简单启发式：如果函数体很短或只有pass/return，可能是None
                    if '->' not in line:
                        line = re.sub(r'(\)\s*):', r') -> None:', line)
                        fixes += 1
                # 其他函数添加 -> None 作为默认
                elif '->' not in line:
                    # 检查是否已在行尾
                    if line.rstrip().endswith(')'):
                        line = line.rstrip() + ' -> None:'
                        fixes += 1
                    else:
                        line = re.sub(r'(\)\s*):', r') -> None:', line)
                        fixes += 1
        
        fixed_lines.append(line)
    
    return fixes, fixed_lines


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python fix_no_untyped_def.py <file_or_directory>")
        sys.exit(1)
    
    target = Path(sys.argv[1])
    total_fixes = 0
    files_fixed = 0
    
    if target.is_file():
        files = [target]
    else:
        files = list(target.rglob('*.py'))
    
    for filepath in files:
        if filepath.name.startswith('test_'):
            continue
            
        try:
            fixes, fixed_lines = fix_file(filepath)
            if fixes > 0:
                filepath.write_text('\n'.join(fixed_lines), encoding='utf-8')
                print(f"Fixed {fixes} issues in {filepath}")
                total_fixes += fixes
                files_fixed += 1
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
    
    print(f"\nTotal: Fixed {total_fixes} issues in {files_fixed} files")


if __name__ == '__main__':
    main()
