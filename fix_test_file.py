#!/usr/bin/env python3
"""Script to fix malformed try/finally blocks in test_persona_agent.py"""

import re

def fix_test_file():
    with open('test_persona_agent.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into lines for easier processing
    lines = content.split('\n')
    
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for the pattern: try: followed by PersonaAgent instantiation
        if 'try:' in line and i + 1 < len(lines) and 'PersonaAgent(test_character_dir)' in lines[i + 1]:
            # Add the try line
            fixed_lines.append(line)
            fixed_lines.append(lines[i + 1])  # PersonaAgent line
            i += 2
            
            # Add the test content within the try block
            while i < len(lines) and not (lines[i].strip().startswith('def ') or lines[i].strip().startswith('class ')):
                if lines[i].strip() == '':
                    fixed_lines.append(lines[i])
                elif lines[i].startswith('        assert') or lines[i].startswith('        #') or 'agent.' in lines[i]:
                    # Indent these lines to be inside the try block
                    fixed_lines.append('    ' + lines[i])
                else:
                    fixed_lines.append(lines[i])
                i += 1
            
            # Add finally block before the next method/class
            fixed_lines.append('        finally:')
            fixed_lines.append('            shutil.rmtree(test_character_dir, ignore_errors=True)')
            fixed_lines.append('')
            
            # Don't increment i here since we want to process the current line
            continue
        else:
            fixed_lines.append(line)
            i += 1
    
    # Write the fixed content
    with open('test_persona_agent.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(fixed_lines))
    
    print("Fixed try/finally blocks in test_persona_agent.py")

if __name__ == "__main__":
    fix_test_file()