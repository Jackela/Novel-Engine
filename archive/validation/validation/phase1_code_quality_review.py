#!/usr/bin/env python3
"""
PHASE 1.2: Code Quality Review and Standards Validation
======================================================

Comprehensive code quality analysis including:
1. Code style and standards compliance
2. Security vulnerability scanning
3. Performance pattern analysis
4. Error handling review
5. Documentation coverage
6. Test coverage analysis
"""

import sys
import os
import ast
import json
import re
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CodeQualityReviewer:
    """Comprehensive code quality analysis."""
    
    def __init__(self):
        self.project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.quality_issues = []
        self.security_issues = []
        self.performance_issues = []
        self.recommendations = []
        
    def analyze_code_style(self) -> Dict[str, Any]:
        """Analyze code style and standards compliance."""
        
        print("📝 ANALYZING CODE STYLE & STANDARDS")
        print("=" * 60)
        
        python_files = list(self.project_root.glob('*.py'))
        
        style_analysis = {
            'files_analyzed': len(python_files),
            'style_issues': [],
            'complexity_scores': {},
            'naming_conventions': {'violations': []},
            'documentation_coverage': {}
        }
        
        for py_file in python_files:
            if 'test_' in py_file.name or py_file.name.startswith('test_'):
                continue  # Skip test files for now
                
            print(f"🔍 Analyzing: {py_file.name}")
            
            try:
                file_analysis = self._analyze_single_file(py_file)
                style_analysis['complexity_scores'][py_file.name] = file_analysis['complexity']
                style_analysis['style_issues'].extend(file_analysis['style_issues'])
                style_analysis['naming_conventions']['violations'].extend(file_analysis['naming_issues'])
                style_analysis['documentation_coverage'][py_file.name] = file_analysis['doc_coverage']
                
                print(f"   📊 Complexity: {file_analysis['complexity']:.2f}")
                print(f"   📚 Doc Coverage: {file_analysis['doc_coverage']:.1%}")
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")
                style_analysis['style_issues'].append(f"Failed to analyze {py_file.name}: {e}")
        
        # Calculate overall scores
        avg_complexity = sum(style_analysis['complexity_scores'].values()) / len(style_analysis['complexity_scores']) if style_analysis['complexity_scores'] else 0
        avg_doc_coverage = sum(style_analysis['documentation_coverage'].values()) / len(style_analysis['documentation_coverage']) if style_analysis['documentation_coverage'] else 0
        
        print(f"\n📊 STYLE ANALYSIS SUMMARY:")
        print(f"   📁 Files analyzed: {style_analysis['files_analyzed']}")
        print(f"   🧮 Average complexity: {avg_complexity:.2f}")
        print(f"   📚 Average doc coverage: {avg_doc_coverage:.1%}")
        print(f"   ⚠️  Style issues found: {len(style_analysis['style_issues'])}")
        print(f"   📛 Naming violations: {len(style_analysis['naming_conventions']['violations'])}")
        
        return style_analysis
    
    def _analyze_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single Python file for quality metrics."""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {
                'complexity': float('inf'),
                'style_issues': [f"Syntax error: {e}"],
                'naming_issues': [],
                'doc_coverage': 0.0
            }
        
        analyzer = ASTAnalyzer()
        analyzer.visit(tree)
        
        return {
            'complexity': analyzer.calculate_complexity(),
            'style_issues': analyzer.style_issues,
            'naming_issues': analyzer.naming_issues,
            'doc_coverage': analyzer.calculate_doc_coverage()
        }
    
    def analyze_security_patterns(self) -> Dict[str, Any]:
        """Analyze code for security vulnerabilities and patterns."""
        
        print("\n🛡️  ANALYZING SECURITY PATTERNS")
        print("=" * 60)
        
        python_files = list(self.project_root.glob('*.py'))
        
        security_analysis = {
            'files_scanned': len(python_files),
            'vulnerabilities': [],
            'security_patterns': {
                'sql_injection_risks': [],
                'xss_risks': [],
                'path_traversal_risks': [],
                'hardcoded_secrets': [],
                'unsafe_deserialization': [],
                'command_injection_risks': []
            },
            'security_score': 0.0
        }
        
        security_patterns = {
            'sql_injection': [r'execute\([^)]*%', r'query\([^)]*%', r'\.format\([^)]*\).*execute'],
            'xss_risks': [r'render_template_string\(.*request\.', r'Markup\(.*request\.'],
            'path_traversal': [r'open\([^)]*\+', r'os\.path\.join\(.*request\.'],
            'hardcoded_secrets': [r'password\s*=\s*["\'][^"\']{8,}', r'api_key\s*=\s*["\'][^"\']{20,}', r'token\s*=\s*["\'][^"\']{16,}'],
            'unsafe_deserialization': [r'pickle\.loads?', r'yaml\.load\(', r'eval\('],
            'command_injection': [r'os\.system\(', r'subprocess\.[^)]*shell\s*=\s*True', r'exec\(']
        }
        
        total_issues = 0
        
        for py_file in python_files:
            print(f"🔒 Scanning: {py_file.name}")
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_issues = 0
                
                for vuln_type, patterns in security_patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            issue = {
                                'file': py_file.name,
                                'type': vuln_type,
                                'line': line_num,
                                'pattern': pattern,
                                'context': match.group(0)
                            }
                            security_analysis['security_patterns'][vuln_type].append(issue)
                            file_issues += 1
                            total_issues += 1
                
                print(f"   🚨 Issues found: {file_issues}")
                
            except Exception as e:
                print(f"   ❌ Scan failed: {e}")
        
        # Calculate security score (higher is better)
        total_lines = sum(len(open(f, 'r', encoding='utf-8').readlines()) for f in python_files if f.exists())
        security_analysis['security_score'] = max(0, 1.0 - (total_issues / max(total_lines / 100, 1)))
        
        print(f"\n🛡️  SECURITY ANALYSIS SUMMARY:")
        print(f"   📁 Files scanned: {security_analysis['files_scanned']}")
        print(f"   🚨 Total vulnerabilities: {total_issues}")
        print(f"   📊 Security score: {security_analysis['security_score']:.1%}")
        
        if total_issues == 0:
            print(f"   ✅ No obvious security vulnerabilities detected")
        else:
            print(f"   ⚠️  Security issues require review")
        
        return security_analysis
    
    def analyze_performance_patterns(self) -> Dict[str, Any]:
        """Analyze code for performance anti-patterns."""
        
        print("\n⚡ ANALYZING PERFORMANCE PATTERNS")
        print("=" * 60)
        
        python_files = list(self.project_root.glob('*.py'))
        
        performance_analysis = {
            'files_analyzed': len(python_files),
            'performance_issues': [],
            'optimization_opportunities': [],
            'performance_score': 0.0
        }
        
        performance_patterns = {
            'inefficient_loops': [
                r'for.*in.*range\(len\(',  # Use enumerate instead
                r'while.*len\(',  # Potential infinite loop risks
            ],
            'memory_issues': [
                r'\.append\(.*\).*for.*in',  # List comprehension might be better
                r'list\(.*\.values\(\)\)',  # Direct iteration might be better
            ],
            'io_issues': [
                r'open\([^)]*\)(?!\s*as)',  # Files not properly closed
                r'print\(',  # Debug prints left in production code
            ],
            'string_operations': [
                r'\+.*\+.*\+',  # Multiple string concatenations
                r'\.format\(.*\.format\(',  # Nested format calls
            ]
        }
        
        total_issues = 0
        
        for py_file in python_files:
            print(f"⚡ Analyzing: {py_file.name}")
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_issues = 0
                
                for issue_type, patterns in performance_patterns.items():
                    for pattern in patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for match in matches:
                            line_num = content[:match.start()].count('\n') + 1
                            issue = {
                                'file': py_file.name,
                                'type': issue_type,
                                'line': line_num,
                                'pattern': pattern,
                                'context': match.group(0)[:50] + '...'
                            }
                            performance_analysis['performance_issues'].append(issue)
                            file_issues += 1
                            total_issues += 1
                
                print(f"   ⚠️  Issues found: {file_issues}")
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")
        
        # Calculate performance score
        total_lines = sum(len(open(f, 'r', encoding='utf-8').readlines()) for f in python_files if f.exists())
        performance_analysis['performance_score'] = max(0, 1.0 - (total_issues / max(total_lines / 50, 1)))
        
        print(f"\n⚡ PERFORMANCE ANALYSIS SUMMARY:")
        print(f"   📁 Files analyzed: {performance_analysis['files_analyzed']}")
        print(f"   ⚠️  Performance issues: {total_issues}")
        print(f"   📊 Performance score: {performance_analysis['performance_score']:.1%}")
        
        return performance_analysis
    
    def analyze_error_handling(self) -> Dict[str, Any]:
        """Analyze error handling patterns and coverage."""
        
        print("\n🚨 ANALYZING ERROR HANDLING")
        print("=" * 60)
        
        python_files = list(self.project_root.glob('*.py'))
        
        error_analysis = {
            'files_analyzed': len(python_files),
            'error_handling_patterns': {},
            'coverage_score': 0.0,
            'missing_handlers': [],
            'good_practices': []
        }
        
        total_functions = 0
        functions_with_error_handling = 0
        
        for py_file in python_files:
            print(f"🚨 Analyzing: {py_file.name}")
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Count functions and error handling
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_functions += 1
                        
                        # Check if function has try/except blocks
                        has_error_handling = False
                        for child in ast.walk(node):
                            if isinstance(child, ast.ExceptHandler):
                                has_error_handling = True
                                functions_with_error_handling += 1
                                break
                        
                        if not has_error_handling:
                            error_analysis['missing_handlers'].append(f"{py_file.name}:{node.name}")
                
                # Count error handling patterns
                try_blocks = len(re.findall(r'try:', content))
                except_blocks = len(re.findall(r'except.*:', content))
                finally_blocks = len(re.findall(r'finally:', content))
                
                error_analysis['error_handling_patterns'][py_file.name] = {
                    'try_blocks': try_blocks,
                    'except_blocks': except_blocks,
                    'finally_blocks': finally_blocks,
                }
                
                print(f"   📊 Try/Except blocks: {try_blocks}/{except_blocks}")
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")
        
        # Calculate coverage score
        error_analysis['coverage_score'] = functions_with_error_handling / max(total_functions, 1)
        
        print(f"\n🚨 ERROR HANDLING SUMMARY:")
        print(f"   📁 Files analyzed: {error_analysis['files_analyzed']}")
        print(f"   🔧 Total functions: {total_functions}")
        print(f"   ✅ Functions with error handling: {functions_with_error_handling}")
        print(f"   📊 Coverage score: {error_analysis['coverage_score']:.1%}")
        
        return error_analysis
    
    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive code quality report."""
        
        print("\n" + "=" * 80)
        print("🏁 PHASE 1.2: CODE QUALITY REVIEW SUMMARY")
        print("=" * 80)
        
        # Run all analyses
        style_analysis = self.analyze_code_style()
        security_analysis = self.analyze_security_patterns()
        performance_analysis = self.analyze_performance_patterns()
        error_analysis = self.analyze_error_handling()
        
        # Calculate overall quality score
        scores = {
            'style_score': 1.0 - (len(style_analysis['style_issues']) / 100),  # Arbitrary threshold
            'security_score': security_analysis['security_score'],
            'performance_score': performance_analysis['performance_score'],
            'error_handling_score': error_analysis['coverage_score']
        }
        
        # Ensure all scores are between 0 and 1
        scores = {k: max(0, min(1, v)) for k, v in scores.items()}
        
        overall_quality = sum(scores.values()) / len(scores)
        
        print(f"\n📊 CODE QUALITY METRICS:")
        print(f"   📝 Style Score: {scores['style_score']:.1%}")
        print(f"   🛡️  Security Score: {scores['security_score']:.1%}")
        print(f"   ⚡ Performance Score: {scores['performance_score']:.1%}")
        print(f"   🚨 Error Handling Score: {scores['error_handling_score']:.1%}")
        print(f"   🎯 Overall Quality: {overall_quality:.1%}")
        
        # Quality assessment
        if overall_quality >= 0.8:
            quality_status = "EXCELLENT"
            print(f"\n✅ CODE QUALITY STATUS: EXCELLENT - Production ready")
        elif overall_quality >= 0.6:
            quality_status = "GOOD"
            print(f"\n⚠️  CODE QUALITY STATUS: GOOD - Minor improvements recommended")
        else:
            quality_status = "NEEDS_IMPROVEMENT"
            print(f"\n❌ CODE QUALITY STATUS: NEEDS IMPROVEMENT - Address issues before production")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(style_analysis, security_analysis, performance_analysis, error_analysis)
        
        if recommendations:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in recommendations[:5]:  # Show top 5
                print(f"   • {rec}")
        
        return {
            'style_analysis': style_analysis,
            'security_analysis': security_analysis,
            'performance_analysis': performance_analysis,
            'error_analysis': error_analysis,
            'quality_scores': scores,
            'overall_quality': overall_quality,
            'quality_status': quality_status,
            'recommendations': recommendations
        }
    
    def _generate_recommendations(self, style_analysis, security_analysis, performance_analysis, error_analysis) -> List[str]:
        """Generate quality improvement recommendations."""
        
        recommendations = []
        
        # Style recommendations
        if len(style_analysis['style_issues']) > 0:
            recommendations.append(f"Address {len(style_analysis['style_issues'])} style issues for better maintainability")
        
        # Security recommendations
        total_security_issues = sum(len(issues) for issues in security_analysis['security_patterns'].values())
        if total_security_issues > 0:
            recommendations.append(f"Review {total_security_issues} potential security vulnerabilities")
        
        # Performance recommendations
        if len(performance_analysis['performance_issues']) > 0:
            recommendations.append(f"Optimize {len(performance_analysis['performance_issues'])} performance bottlenecks")
        
        # Error handling recommendations
        if error_analysis['coverage_score'] < 0.7:
            missing_count = len(error_analysis['missing_handlers'])
            recommendations.append(f"Add error handling to {missing_count} functions for better reliability")
        
        # Documentation recommendations
        avg_doc_coverage = sum(style_analysis['documentation_coverage'].values()) / len(style_analysis['documentation_coverage']) if style_analysis['documentation_coverage'] else 0
        if avg_doc_coverage < 0.5:
            recommendations.append("Improve documentation coverage to at least 50%")
        
        return recommendations


class ASTAnalyzer(ast.NodeVisitor):
    """AST-based code analysis for quality metrics."""
    
    def __init__(self):
        self.complexity = 0
        self.functions = []
        self.classes = []
        self.style_issues = []
        self.naming_issues = []
        self.docstring_count = 0
        self.total_functions = 0
        
    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        self.total_functions += 1
        
        # Check if function has docstring
        if ast.get_docstring(node):
            self.docstring_count += 1
        
        # Check naming convention
        if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
            self.naming_issues.append(f"Function '{node.name}' doesn't follow snake_case convention")
        
        # Count complexity indicators
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                self.complexity += 1
            elif isinstance(child, ast.BoolOp):
                self.complexity += len(child.values) - 1
        
        self.functions.append(node.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Visit class definitions."""
        
        # Check naming convention
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
            self.naming_issues.append(f"Class '{node.name}' doesn't follow PascalCase convention")
        
        self.classes.append(node.name)
        self.generic_visit(node)
    
    def calculate_complexity(self) -> float:
        """Calculate cyclomatic complexity score."""
        base_complexity = 1  # Base complexity
        return base_complexity + self.complexity
    
    def calculate_doc_coverage(self) -> float:
        """Calculate documentation coverage."""
        if self.total_functions == 0:
            return 1.0  # No functions means 100% coverage
        return self.docstring_count / self.total_functions


def main():
    """Execute Phase 1.2 Code Quality Review."""
    
    print("📊 STORYFORGE AI - PHASE 1.2: CODE QUALITY REVIEW")
    print("=" * 80)
    print("Comprehensive analysis of code quality, security, and performance")
    print("=" * 80)
    
    reviewer = CodeQualityReviewer()
    report = reviewer.generate_quality_report()
    
    # Save report
    output_dir = Path(__file__).parent
    report_path = output_dir / 'phase1_2_code_quality_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n💾 Code quality report saved: {report_path}")
    
    return report['overall_quality'] >= 0.6

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)