#!/usr/bin/env python3
"""
Team Alpha - Batch Fix Script for no-untyped-def errors
批量修复no-untyped-def错误
"""

import re
import subprocess
from pathlib import Path
from typing import List, Tuple


def get_mypy_errors(path: str = "src/") -> List[str]:
    """获取mypy错误列表"""
    result = subprocess.run(
        ["python", "-m", "mypy", path, "--ignore-missing-imports", "--no-error-summary"],
        capture_output=True,
        text=True,
    )
    return [line for line in result.stderr.split("\n") if "no-untyped-def" in line]


def parse_error_line(error_line: str) -> Tuple[str, int, str]:
    """解析错误行
    
    Returns:
        (文件路径, 行号, 错误消息)
    """
    # 格式: src/file.py:123: error: message [no-untyped-def]
    match = re.match(r'^([^:]+):(\d+): error: (.+) \[no-untyped-def\]$', error_line)
    if match:
        return match.group(1), int(match.group(2)), match.group(3)
    return "", 0, ""


def fix_file_no_untyped_def(filepath: Path) -> int:
    """修复文件中的no-untyped-def错误
    
    Returns:
        修复的错误数量
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return 0
    
    fixes = 0
    new_lines = []
    
    for i, line in enumerate(lines):
        original = line
        
        # 匹配函数定义模式
        # def funcname(...): 或 def funcname(...) -> Type:
        func_pattern = r'^(\s*)def\s+(\w+)\s*\('
        match = re.match(func_pattern, line)
        
        if match:
            indent = match.group(1)
            func_name = match.group(2)
            
            # 检查是否已经有返回类型注解
            if '->' not in line or line.count('->') == 0:
                # 查找行尾或下一行是否有):
                j = i
                paren_count = 0
                found_end = False
                end_line_idx = i
                
                while j < len(lines) and not found_end:
                    for char in lines[j]:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                            if paren_count == 0:
                                found_end = True
                                end_line_idx = j
                                break
                    if found_end:
                        break
                    j += 1
                
                if found_end:
                    # 检查是否在)后已经有类型注解
                    end_line = lines[end_line_idx]
                    close_paren_idx = end_line.rfind(')')
                    rest = end_line[close_paren_idx+1:].strip()
                    
                    if not rest.startswith('->') and ':' in rest:
                        # 添加 -> None
                        colon_idx = end_line.find(':', close_paren_idx)
                        if colon_idx > 0:
                            new_end_line = end_line[:colon_idx] + ' -> None' + end_line[colon_idx:]
                            lines[end_line_idx] = new_end_line
                            fixes += 1
        
        new_lines.append(lines[i])
    
    if fixes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"Fixed {fixes} issues in {filepath}")
    
    return fixes


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python batch_fix_no_untyped_def.py <directory>")
        sys.exit(1)
    
    target_dir = Path(sys.argv[1])
    if not target_dir.exists():
        print(f"Directory not found: {target_dir}")
        sys.exit(1)
    
    # 获取Python文件列表
    py_files = list(target_dir.rglob("*.py"))
    
    print(f"Found {len(py_files)} Python files in {target_dir}")
    print("Scanning for no-untyped-def errors...")
    
    # 获取当前错误列表
    errors = get_mypy_errors(str(target_dir))
    print(f"Found {len(errors)} no-untyped-def errors")
    
    # 按文件分组错误
    files_with_errors = set()
    for error in errors:
        filepath, _, _ = parse_error_line(error)
        if filepath:
            files_with_errors.add(filepath)
    
    print(f"Errors in {len(files_with_errors)} files")
    
    # 修复每个文件
    total_fixes = 0
    for filepath_str in sorted(files_with_errors):
        filepath = Path(filepath_str)
        if filepath.exists():
            fixes = fix_file_no_untyped_def(filepath)
            total_fixes += fixes
    
    print(f"\nTotal fixes: {total_fixes}")
    
    # 重新检查错误
    remaining_errors = get_mypy_errors(str(target_dir))
    print(f"Remaining no-untyped-def errors: {len(remaining_errors)}")


if __name__ == "__main__":
    main()
