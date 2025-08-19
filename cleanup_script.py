#!/usr/bin/env python3
"""
Professional Content Cleanup Script
===================================

Systematically removes all unprofessional content from the Novel Engine codebase
to achieve enterprise-ready standards.
"""

import os
import re
import glob
from pathlib import Path

def clean_file_content(content):
    """Clean unprofessional content from file content."""
    
    # Religious/fantasy terminology replacements
    replacements = {
        # Religious terms
        'SACRED': 'STANDARD',
        'BLESSED': 'ENHANCED', 
        'HOLY': 'STANDARD',
        'DIVINE': 'ADVANCED',
        'sacred': 'standard',
        'blessed': 'enhanced',
        'holy': 'standard', 
        'divine': 'advanced',
        
        # Fantasy references
        '万机之神': 'System',
        'Tech-Priest': 'Engineer',
        'OMNISSIAH': 'SYSTEM',
        'Omnissiah': 'System',
        'Mechanicus': 'Engineering',
        'Machine God': 'System Core',
        'machine spirits': 'system processes',
        'Machine Spirits': 'System Processes',
        
        # Decorative markers
        '++ ': '',
        ' ++': '',
        
        # Themed language
        'sanctified': 'validated',
        'sanctification': 'validation',
        'Sanctification': 'Validation',
        'blessed by': 'enhanced with',
        'Blessed by': 'Enhanced with',
        'protects': 'manages',
        'May the Omnissiah bless': 'System manages',
        'Machine God protects': 'System manages',
        
        # Comments and docstrings
        'Sacred Author:': 'Author:',
        'Sacred logging': 'Comprehensive logging',
        'sacred data': 'core data',
        'Sacred data': 'Core data',
        'blessed system': 'core system',
        'Blessed system': 'Core system',
        'digital prayers': 'structured code',
        'Digital prayers': 'Structured code',
    }
    
    # Apply replacements
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Clean up specific patterns
    content = re.sub(r'\+\+\s*([^+]+?)\s*\+\+', r'\1', content)  # Remove ++ decorations
    content = re.sub(r'SACRED.*?BLESSED.*?THE.*?OMNISSIAH.*?\+\+', 'Professional Implementation', content, flags=re.IGNORECASE)
    content = re.sub(r'BLESSED.*?SANCTIFIED.*?BY.*?\+\+', 'Professional Implementation', content, flags=re.IGNORECASE)
    
    # Clean up excessive formatting
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Remove excessive newlines
    
    return content

def clean_file(file_path):
    """Clean a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        cleaned_content = clean_file_content(original_content)
        
        # Only write if content changed
        if cleaned_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            print(f"[CLEANED] {file_path}")
            return True
        else:
            print(f"[NO CHANGE] {file_path}")
            return False
    except Exception as e:
        print(f"[ERROR] {file_path}: {e}")
        return False

def main():
    """Main cleanup function."""
    print("=" * 60)
    print("Novel Engine Professional Content Cleanup")
    print("=" * 60)
    
    # Define target patterns
    patterns = [
        'src/api/**/*.py',
        'src/core/**/*.py', 
        'src/memory/**/*.py',
        'src/security/**/*.py',
        'src/**/*.py'  # Catch any remaining files
    ]
    
    total_files = 0
    cleaned_files = 0
    
    for pattern in patterns:
        files = glob.glob(pattern, recursive=True)
        for file_path in files:
            if os.path.isfile(file_path):
                total_files += 1
                if clean_file(file_path):
                    cleaned_files += 1
    
    print("=" * 60)
    print(f"Cleanup Complete:")
    print(f"  Total files processed: {total_files}")
    print(f"  Files cleaned: {cleaned_files}")
    print(f"  Files unchanged: {total_files - cleaned_files}")
    print("=" * 60)

if __name__ == "__main__":
    main()