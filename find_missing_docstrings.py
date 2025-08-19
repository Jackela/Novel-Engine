#!/usr/bin/env python3
"""
Script to find missing docstrings in the Novel Engine codebase.
"""

import os
import ast
import re
from typing import List, Dict, Tuple, Set
from pathlib import Path

class DocstringAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to find missing docstrings."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.missing_docstrings = []
        self.stats = {
            'total_functions': 0,
            'total_classes': 0,
            'functions_with_docstrings': 0,
            'classes_with_docstrings': 0
        }
    
    def has_docstring(self, node) -> bool:
        """Check if a node has a docstring."""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return True
        return False
    
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.stats['total_functions'] += 1
        
        # Skip private functions that start with underscore
        if not node.name.startswith('_'):
            if not self.has_docstring(node):
                self.missing_docstrings.append({
                    'type': 'function',
                    'name': node.name,
                    'line': node.lineno,
                    'file': self.filepath
                })
            else:
                self.stats['functions_with_docstrings'] += 1
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.visit_FunctionDef(node)  # Same logic as regular functions
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        self.stats['total_classes'] += 1
        
        if not self.has_docstring(node):
            self.missing_docstrings.append({
                'type': 'class',
                'name': node.name,
                'line': node.lineno,
                'file': self.filepath
            })
        else:
            self.stats['classes_with_docstrings'] += 1
        
        self.generic_visit(node)

def analyze_file(filepath: str) -> Tuple[List[Dict], Dict]:
    """Analyze a single Python file for missing docstrings."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = DocstringAnalyzer(filepath)
        analyzer.visit(tree)
        
        return analyzer.missing_docstrings, analyzer.stats
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return [], {'total_functions': 0, 'total_classes': 0, 'functions_with_docstrings': 0, 'classes_with_docstrings': 0}

def find_python_files(directory: str) -> List[str]:
    """Find all Python files in directory."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def categorize_missing_docstrings(missing_docstrings: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize missing docstrings by priority area."""
    categories = {
        'core_system': [],
        'api_endpoints': [],
        'security_components': [],
        'memory_caching': [],
        'main_application': [],
        'utility_support': []
    }
    
    for item in missing_docstrings:
        filepath = item['file'].replace('\\', '/')
        
        if '/core/' in filepath:
            categories['core_system'].append(item)
        elif '/api/' in filepath:
            categories['api_endpoints'].append(item)
        elif '/security/' in filepath:
            categories['security_components'].append(item)
        elif '/memory/' in filepath or '/caching/' in filepath:
            categories['memory_caching'].append(item)
        elif 'persona_agent.py' in filepath or 'system_orchestrator.py' in filepath:
            categories['main_application'].append(item)
        else:
            categories['utility_support'].append(item)
    
    return categories

def main():
    """Main analysis function."""
    src_directory = "src"
    
    if not os.path.exists(src_directory):
        print(f"Error: {src_directory} directory not found")
        return
    
    print("Analyzing Novel Engine codebase for missing docstrings...")
    print("=" * 60)
    
    python_files = find_python_files(src_directory)
    all_missing = []
    total_stats = {'total_functions': 0, 'total_classes': 0, 'functions_with_docstrings': 0, 'classes_with_docstrings': 0}
    
    for filepath in python_files:
        missing, stats = analyze_file(filepath)
        all_missing.extend(missing)
        
        for key in total_stats:
            total_stats[key] += stats[key]
    
    # Categorize results
    categorized = categorize_missing_docstrings(all_missing)
    
    print(f"Total Python files analyzed: {len(python_files)}")
    print(f"Total functions: {total_stats['total_functions']}")
    print(f"Total classes: {total_stats['total_classes']}")
    print(f"Functions with docstrings: {total_stats['functions_with_docstrings']}")
    print(f"Classes with docstrings: {total_stats['classes_with_docstrings']}")
    print(f"Total missing docstrings: {len(all_missing)}")
    print("=" * 60)
    
    # Priority order
    priority_order = [
        ('core_system', 'Core System Components'),
        ('api_endpoints', 'API Endpoints'),
        ('security_components', 'Security Components'),
        ('memory_caching', 'Memory and Caching Systems'),
        ('main_application', 'Main Application Files'),
        ('utility_support', 'Utility and Support Classes')
    ]
    
    for category_key, category_name in priority_order:
        items = categorized[category_key]
        if items:
            print(f"\n{category_name} ({len(items)} missing docstrings):")
            print("-" * 40)
            
            # Group by file
            by_file = {}
            for item in items:
                if item['file'] not in by_file:
                    by_file[item['file']] = []
                by_file[item['file']].append(item)
            
            for filepath, file_items in sorted(by_file.items()):
                print(f"\nFile: {filepath}")
                for item in file_items:
                    print(f"  Line {item['line']}: {item['type']} '{item['name']}'")
    
    # Summary recommendations
    print("\n" + "=" * 60)
    print("DOCSTRING STANDARDIZATION RECOMMENDATIONS:")
    print("=" * 60)
    
    print("\nHIGHEST PRIORITY (Critical Components):")
    for category_key, category_name in priority_order[:4]:
        count = len(categorized[category_key])
        if count > 0:
            print(f"  - {category_name}: {count} missing docstrings")
    
    print(f"\nTotal missing docstrings to add: {len(all_missing)}")
    
    # Calculate coverage percentages
    func_coverage = (total_stats['functions_with_docstrings'] / max(total_stats['total_functions'], 1)) * 100
    class_coverage = (total_stats['classes_with_docstrings'] / max(total_stats['total_classes'], 1)) * 100
    
    print(f"Current function docstring coverage: {func_coverage:.1f}%")
    print(f"Current class docstring coverage: {class_coverage:.1f}%")
    print(f"Target: 100% coverage on critical components")

if __name__ == "__main__":
    main()