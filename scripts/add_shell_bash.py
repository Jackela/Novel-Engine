#!/usr/bin/env python3
"""
Add 'shell: bash' to all run blocks in GitHub workflows
为所有GitHub workflows的run块添加'shell: bash'
"""

import re
import sys
from pathlib import Path


def add_shell_bash(content: str) -> str:
    """Add 'shell: bash' before 'run: |' blocks if not already present."""
    lines = content.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a 'run: |' line
        if re.match(r'^(\s+)- name:', line):
            # Found a step, check if next non-comment line is 'run: |'
            result.append(line)
            i += 1
            
            # Skip any 'if:' or other attributes before 'run:'
            while i < len(lines):
                current_line = lines[i]
                
                # Check if we found 'run: |'
                if re.match(r'^(\s+)run: \|', current_line):
                    # Check if previous line already has 'shell: bash'
                    if not (result and 'shell: bash' in result[-1]):
                        # Get indentation from 'run:' line
                        indent = re.match(r'^(\s+)', current_line).group(1)
                        # Insert 'shell: bash' before 'run: |'
                        result.append(f'{indent}shell: bash')
                    result.append(current_line)
                    i += 1
                    break
                else:
                    result.append(current_line)
                    i += 1
                    # If we hit another step or job, stop looking for 'run:'
                    if re.match(r'^(\s+)- name:|^(\s+)\w+:', current_line):
                        break
        else:
            result.append(line)
            i += 1
    
    return '\n'.join(result)


def process_workflow(filepath: Path) -> bool:
    """Process a single workflow file."""
    print(f"Processing: {filepath.name}")
    
    try:
        content = filepath.read_text(encoding='utf-8')
        
        # Count existing 'shell: bash'
        original_count = content.count('shell: bash')
        
        # Add shell: bash where needed
        updated_content = add_shell_bash(content)
        
        # Count new 'shell: bash'
        new_count = updated_content.count('shell: bash')
        
        if new_count > original_count:
            filepath.write_text(updated_content, encoding='utf-8')
            print(f"  ✅ Added {new_count - original_count} 'shell: bash' statements")
            return True
        else:
            print(f"  ℹ️  No changes needed (already has {original_count} shell declarations)")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Main entry point."""
    workflows_dir = Path('.github/workflows')
    
    if not workflows_dir.exists():
        print(f"❌ Workflows directory not found: {workflows_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("Adding 'shell: bash' to workflow run blocks")
    print("为workflow run块添加'shell: bash'")
    print("=" * 60)
    print()
    
    # Process all .yml files
    yml_files = sorted(workflows_dir.glob('*.yml'))
    modified_count = 0
    
    for yml_file in yml_files:
        if process_workflow(yml_file):
            modified_count += 1
        print()
    
    print("=" * 60)
    print(f"✅ Modified {modified_count} files")
    print(f"✅ 修改了 {modified_count} 个文件")
    print("=" * 60)


if __name__ == '__main__':
    main()
