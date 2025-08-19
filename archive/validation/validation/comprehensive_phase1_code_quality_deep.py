#!/usr/bin/env python3
"""
StoryForge AI - Phase 1: Deep Code Quality Analysis
Comprehensive AST-based code analysis with advanced metrics
"""

import ast
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import re

class ASTAnalyzer(ast.NodeVisitor):
    """AST-based code analysis for deep quality metrics"""
    
    def __init__(self):
        self.metrics = {
            "complexity_metrics": {
                "cyclomatic_complexity": 0,
                "cognitive_complexity": 0,
                "nesting_depth": 0,
                "max_nesting_depth": 0
            },
            "structure_metrics": {
                "classes": [],
                "functions": [],
                "imports": [],
                "variables": set()
            },
            "quality_indicators": {
                "long_functions": [],
                "complex_functions": [],
                "deep_nesting": [],
                "large_classes": []
            },
            "design_patterns": {
                "singleton_pattern": False,
                "factory_pattern": False,
                "observer_pattern": False,
                "strategy_pattern": False
            }
        }
        self.current_function = None
        self.current_class = None
        self.nesting_level = 0
    
    def visit_FunctionDef(self, node):
        """Analyze function definitions"""
        self.current_function = node.name
        
        # Calculate function metrics
        function_complexity = self._calculate_function_complexity(node)
        function_length = len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])
        
        function_info = {
            "name": node.name,
            "line_number": node.lineno,
            "length": function_length,
            "complexity": function_complexity,
            "parameters": len(node.args.args),
            "docstring": ast.get_docstring(node) is not None
        }
        
        self.metrics["structure_metrics"]["functions"].append(function_info)
        
        # Identify quality issues
        if function_length > 50:
            self.metrics["quality_indicators"]["long_functions"].append(function_info)
        
        if function_complexity > 10:
            self.metrics["quality_indicators"]["complex_functions"].append(function_info)
        
        # Check for design patterns
        if node.name == "__new__" and self.current_class:
            self.metrics["design_patterns"]["singleton_pattern"] = True
        
        if "create" in node.name.lower() or "make" in node.name.lower():
            self.metrics["design_patterns"]["factory_pattern"] = True
        
        self.generic_visit(node)
        self.current_function = None
    
    def visit_ClassDef(self, node):
        """Analyze class definitions"""
        self.current_class = node.name
        
        # Calculate class metrics
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        attributes = self._count_class_attributes(node)
        class_length = len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])
        
        class_info = {
            "name": node.name,
            "line_number": node.lineno,
            "methods": len(methods),
            "attributes": attributes,
            "length": class_length,
            "docstring": ast.get_docstring(node) is not None,
            "inheritance": len(node.bases)
        }
        
        self.metrics["structure_metrics"]["classes"].append(class_info)
        
        # Identify large classes
        if len(methods) > 20 or class_length > 200:
            self.metrics["quality_indicators"]["large_classes"].append(class_info)
        
        # Check for observer pattern
        method_names = [m.name for m in methods]
        if any(name in method_names for name in ["register", "notify", "update"]):
            self.metrics["design_patterns"]["observer_pattern"] = True
        
        self.generic_visit(node)
        self.current_class = None
    
    def visit_If(self, node):
        """Track conditional complexity and nesting"""
        self.nesting_level += 1
        self.metrics["complexity_metrics"]["max_nesting_depth"] = max(
            self.metrics["complexity_metrics"]["max_nesting_depth"], 
            self.nesting_level
        )
        
        if self.nesting_level > 4:
            self.metrics["quality_indicators"]["deep_nesting"].append({
                "function": self.current_function,
                "class": self.current_class,
                "line": node.lineno,
                "depth": self.nesting_level
            })
        
        self.metrics["complexity_metrics"]["cyclomatic_complexity"] += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_For(self, node):
        """Track loop complexity and nesting"""
        self.nesting_level += 1
        self.metrics["complexity_metrics"]["cyclomatic_complexity"] += 1
        self.metrics["complexity_metrics"]["cognitive_complexity"] += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_While(self, node):
        """Track while loop complexity"""
        self.nesting_level += 1
        self.metrics["complexity_metrics"]["cyclomatic_complexity"] += 1
        self.metrics["complexity_metrics"]["cognitive_complexity"] += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_Try(self, node):
        """Track exception handling complexity"""
        self.metrics["complexity_metrics"]["cyclomatic_complexity"] += len(node.handlers)
        self.generic_visit(node)
    
    def visit_Import(self, node):
        """Track imports"""
        for alias in node.names:
            self.metrics["structure_metrics"]["imports"].append({
                "name": alias.name,
                "alias": alias.asname,
                "type": "import"
            })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        """Track from imports"""
        for alias in node.names:
            self.metrics["structure_metrics"]["imports"].append({
                "module": node.module,
                "name": alias.name,
                "alias": alias.asname,
                "type": "from_import"
            })
        self.generic_visit(node)
    
    def visit_Name(self, node):
        """Track variable usage"""
        if isinstance(node.ctx, ast.Store):
            self.metrics["structure_metrics"]["variables"].add(node.id)
        self.generic_visit(node)
    
    def _calculate_function_complexity(self, node) -> int:
        """Calculate cyclomatic complexity for a function"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.Try):
                complexity += len(child.handlers)
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _count_class_attributes(self, node) -> int:
        """Count class attributes"""
        attributes = 0
        
        for item in node.body:
            if isinstance(item, ast.Assign):
                attributes += len(item.targets)
            elif isinstance(item, ast.AnnAssign):
                attributes += 1
        
        return attributes

class DeepCodeQualityAnalyzer:
    """Comprehensive code quality analysis with advanced metrics"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.analysis_results = {
            "file_analysis": {},
            "aggregate_metrics": {},
            "quality_assessment": {},
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
    
    def run_deep_analysis(self) -> Dict[str, Any]:
        """Execute comprehensive code quality analysis"""
        print("=== PHASE 1: DEEP CODE QUALITY ANALYSIS ===\n")
        
        # 1. Analyze individual files
        print("🔍 1. Performing AST-based file analysis...")
        self._analyze_individual_files()
        
        # 2. Calculate aggregate metrics
        print("\n📊 2. Calculating aggregate quality metrics...")
        self._calculate_aggregate_metrics()
        
        # 3. Assess overall quality
        print("\n⭐ 3. Assessing overall code quality...")
        self._assess_overall_quality()
        
        # 4. Generate recommendations
        print("\n💡 4. Generating quality improvement recommendations...")
        self._generate_quality_recommendations()
        
        # 5. Save detailed report
        self._save_analysis_report()
        
        return self.analysis_results
    
    def _analyze_individual_files(self):
        """Analyze each Python file individually"""
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse AST
                tree = ast.parse(content)
                
                # Analyze with custom AST visitor
                analyzer = ASTAnalyzer()
                analyzer.visit(tree)
                
                # Convert set to list for JSON serialization
                analyzer.metrics["structure_metrics"]["variables"] = list(analyzer.metrics["structure_metrics"]["variables"])
                
                # Additional file-level metrics
                file_metrics = {
                    "file_size": len(content),
                    "line_count": len(content.split('\n')),
                    "blank_lines": len([line for line in content.split('\n') if not line.strip()]),
                    "comment_lines": len([line for line in content.split('\n') if line.strip().startswith('#')]),
                    "ast_metrics": analyzer.metrics
                }
                
                self.analysis_results["file_analysis"][py_file.name] = file_metrics
                
            except SyntaxError as e:
                print(f"   ⚠️ Syntax error in {py_file.name}: {e}")
                self.analysis_results["file_analysis"][py_file.name] = {
                    "error": f"Syntax error: {e}",
                    "analyzable": False
                }
            except Exception as e:
                print(f"   ⚠️ Could not analyze {py_file.name}: {e}")
                self.analysis_results["file_analysis"][py_file.name] = {
                    "error": str(e),
                    "analyzable": False
                }
        
        print(f"   ✅ Analyzed {len([f for f in self.analysis_results['file_analysis'] if 'error' not in self.analysis_results['file_analysis'][f]])} files successfully")
    
    def _calculate_aggregate_metrics(self):
        """Calculate project-wide aggregate metrics"""
        aggregate = {
            "total_files": len(self.analysis_results["file_analysis"]),
            "total_lines": 0,
            "total_functions": 0,
            "total_classes": 0,
            "total_complexity": 0,
            "average_complexity_per_function": 0,
            "documentation_coverage": {
                "functions_with_docs": 0,
                "classes_with_docs": 0,
                "total_functions": 0,
                "total_classes": 0,
                "function_doc_percentage": 0,
                "class_doc_percentage": 0
            },
            "quality_distribution": {
                "simple_functions": 0,
                "moderate_functions": 0,
                "complex_functions": 0,
                "very_complex_functions": 0
            },
            "design_patterns_usage": {
                "singleton": 0,
                "factory": 0,
                "observer": 0,
                "strategy": 0
            }
        }
        
        for filename, file_data in self.analysis_results["file_analysis"].items():
            if "error" in file_data:
                continue
            
            # Aggregate basic metrics
            aggregate["total_lines"] += file_data.get("line_count", 0)
            
            ast_metrics = file_data.get("ast_metrics", {})
            functions = ast_metrics.get("structure_metrics", {}).get("functions", [])
            classes = ast_metrics.get("structure_metrics", {}).get("classes", [])
            
            aggregate["total_functions"] += len(functions)
            aggregate["total_classes"] += len(classes)
            
            # Calculate complexity metrics
            for func in functions:
                complexity = func.get("complexity", 0)
                aggregate["total_complexity"] += complexity
                
                # Classify function complexity
                if complexity <= 5:
                    aggregate["quality_distribution"]["simple_functions"] += 1
                elif complexity <= 10:
                    aggregate["quality_distribution"]["moderate_functions"] += 1
                elif complexity <= 20:
                    aggregate["quality_distribution"]["complex_functions"] += 1
                else:
                    aggregate["quality_distribution"]["very_complex_functions"] += 1
                
                # Documentation coverage
                if func.get("docstring"):
                    aggregate["documentation_coverage"]["functions_with_docs"] += 1
            
            aggregate["documentation_coverage"]["total_functions"] += len(functions)
            
            # Class documentation coverage
            for cls in classes:
                if cls.get("docstring"):
                    aggregate["documentation_coverage"]["classes_with_docs"] += 1
            
            aggregate["documentation_coverage"]["total_classes"] += len(classes)
            
            # Design patterns
            patterns = ast_metrics.get("design_patterns", {})
            for pattern, detected in patterns.items():
                if detected:
                    pattern_key = pattern.replace("_pattern", "")
                    if pattern_key in aggregate["design_patterns_usage"]:
                        aggregate["design_patterns_usage"][pattern_key] += 1
        
        # Calculate averages and percentages
        if aggregate["total_functions"] > 0:
            aggregate["average_complexity_per_function"] = aggregate["total_complexity"] / aggregate["total_functions"]
            aggregate["documentation_coverage"]["function_doc_percentage"] = (
                aggregate["documentation_coverage"]["functions_with_docs"] / 
                aggregate["documentation_coverage"]["total_functions"] * 100
            )
        
        if aggregate["total_classes"] > 0:
            aggregate["documentation_coverage"]["class_doc_percentage"] = (
                aggregate["documentation_coverage"]["classes_with_docs"] / 
                aggregate["documentation_coverage"]["total_classes"] * 100
            )
        
        self.analysis_results["aggregate_metrics"] = aggregate
        
        # Print key metrics
        print(f"   📁 Total Files: {aggregate['total_files']}")
        print(f"   📝 Total Lines: {aggregate['total_lines']}")
        print(f"   ⚙️ Functions: {aggregate['total_functions']}, Classes: {aggregate['total_classes']}")
        print(f"   🧮 Average Function Complexity: {aggregate['average_complexity_per_function']:.2f}")
        print(f"   📚 Documentation Coverage: {aggregate['documentation_coverage']['function_doc_percentage']:.1f}% functions, {aggregate['documentation_coverage']['class_doc_percentage']:.1f}% classes")
    
    def _assess_overall_quality(self):
        """Assess overall code quality with detailed scoring"""
        assessment = {
            "complexity_score": 0,
            "documentation_score": 0,
            "structure_score": 0,
            "maintainability_score": 0,
            "overall_score": 0,
            "grade": "F",
            "quality_level": "Poor"
        }
        
        aggregate = self.analysis_results["aggregate_metrics"]
        
        # 1. Complexity Score (0-100)
        avg_complexity = aggregate.get("average_complexity_per_function", 0)
        if avg_complexity <= 5:
            assessment["complexity_score"] = 100
        elif avg_complexity <= 10:
            assessment["complexity_score"] = 80
        elif avg_complexity <= 15:
            assessment["complexity_score"] = 60
        elif avg_complexity <= 20:
            assessment["complexity_score"] = 40
        else:
            assessment["complexity_score"] = 20
        
        # 2. Documentation Score (0-100)
        func_doc_pct = aggregate.get("documentation_coverage", {}).get("function_doc_percentage", 0)
        class_doc_pct = aggregate.get("documentation_coverage", {}).get("class_doc_percentage", 0)
        assessment["documentation_score"] = (func_doc_pct + class_doc_pct) / 2
        
        # 3. Structure Score (0-100)
        quality_dist = aggregate.get("quality_distribution", {})
        total_funcs = sum(quality_dist.values())
        
        if total_funcs > 0:
            simple_pct = quality_dist.get("simple_functions", 0) / total_funcs
            moderate_pct = quality_dist.get("moderate_functions", 0) / total_funcs
            complex_pct = quality_dist.get("complex_functions", 0) / total_funcs
            very_complex_pct = quality_dist.get("very_complex_functions", 0) / total_funcs
            
            # Score based on distribution (prefer simple/moderate functions)
            assessment["structure_score"] = (
                simple_pct * 100 + 
                moderate_pct * 80 + 
                complex_pct * 40 + 
                very_complex_pct * 10
            )
        
        # 4. Maintainability Score (0-100)
        # Based on various factors: complexity, documentation, structure
        maintainability_factors = []
        
        # Factor 1: Low complexity bonus
        if avg_complexity <= 8:
            maintainability_factors.append(30)
        elif avg_complexity <= 12:
            maintainability_factors.append(20)
        else:
            maintainability_factors.append(10)
        
        # Factor 2: Documentation bonus
        if func_doc_pct >= 80:
            maintainability_factors.append(25)
        elif func_doc_pct >= 60:
            maintainability_factors.append(20)
        elif func_doc_pct >= 40:
            maintainability_factors.append(15)
        else:
            maintainability_factors.append(10)
        
        # Factor 3: Design patterns usage
        patterns_used = sum(1 for count in aggregate.get("design_patterns_usage", {}).values() if count > 0)
        maintainability_factors.append(min(20, patterns_used * 5))
        
        # Factor 4: Function size distribution
        if quality_dist.get("simple_functions", 0) + quality_dist.get("moderate_functions", 0) >= total_funcs * 0.8:
            maintainability_factors.append(25)
        else:
            maintainability_factors.append(15)
        
        assessment["maintainability_score"] = sum(maintainability_factors)
        
        # 5. Overall Score (weighted average)
        scores = [
            assessment["complexity_score"] * 0.3,
            assessment["documentation_score"] * 0.25,
            assessment["structure_score"] * 0.25,
            assessment["maintainability_score"] * 0.2
        ]
        assessment["overall_score"] = sum(scores)
        
        # 6. Letter Grade
        if assessment["overall_score"] >= 90:
            assessment["grade"] = "A"
            assessment["quality_level"] = "Excellent"
        elif assessment["overall_score"] >= 80:
            assessment["grade"] = "B"
            assessment["quality_level"] = "Good"
        elif assessment["overall_score"] >= 70:
            assessment["grade"] = "C"
            assessment["quality_level"] = "Acceptable"
        elif assessment["overall_score"] >= 60:
            assessment["grade"] = "D"
            assessment["quality_level"] = "Below Average"
        else:
            assessment["grade"] = "F"
            assessment["quality_level"] = "Poor"
        
        self.analysis_results["quality_assessment"] = assessment
        
        # Print quality assessment
        print(f"   📊 Overall Quality Score: {assessment['overall_score']:.1f}/100 (Grade: {assessment['grade']})")
        print(f"   📈 Quality Level: {assessment['quality_level']}")
        print(f"   🧮 Complexity Score: {assessment['complexity_score']:.1f}/100")
        print(f"   📚 Documentation Score: {assessment['documentation_score']:.1f}/100")
        print(f"   🏗️ Structure Score: {assessment['structure_score']:.1f}/100")
        print(f"   🔧 Maintainability Score: {assessment['maintainability_score']:.1f}/100")
    
    def _generate_quality_recommendations(self):
        """Generate specific quality improvement recommendations"""
        recommendations = []
        
        aggregate = self.analysis_results["aggregate_metrics"]
        assessment = self.analysis_results["quality_assessment"]
        
        # Complexity recommendations
        if assessment["complexity_score"] < 70:
            avg_complexity = aggregate.get("average_complexity_per_function", 0)
            recommendations.append({
                "category": "Complexity",
                "priority": "HIGH",
                "issue": f"Average function complexity is {avg_complexity:.1f}",
                "recommendation": "Refactor complex functions (>10 complexity) into smaller, focused functions",
                "impact": "Improves readability, testability, and maintainability"
            })
        
        # Documentation recommendations
        if assessment["documentation_score"] < 70:
            func_doc_pct = aggregate.get("documentation_coverage", {}).get("function_doc_percentage", 0)
            recommendations.append({
                "category": "Documentation",
                "priority": "MEDIUM",
                "issue": f"Only {func_doc_pct:.1f}% of functions have docstrings",
                "recommendation": "Add comprehensive docstrings to all public functions and classes",
                "impact": "Improves code understanding and maintenance"
            })
        
        # Structure recommendations
        quality_dist = aggregate.get("quality_distribution", {})
        complex_funcs = quality_dist.get("complex_functions", 0) + quality_dist.get("very_complex_functions", 0)
        total_funcs = sum(quality_dist.values())
        
        if total_funcs > 0 and complex_funcs / total_funcs > 0.2:
            recommendations.append({
                "category": "Structure",
                "priority": "HIGH",
                "issue": f"{complex_funcs} functions are overly complex",
                "recommendation": "Break down complex functions using Extract Method refactoring",
                "impact": "Reduces cognitive load and improves code maintainability"
            })
        
        # File-specific recommendations
        for filename, file_data in self.analysis_results["file_analysis"].items():
            if "error" in file_data:
                continue
            
            ast_metrics = file_data.get("ast_metrics", {})
            quality_indicators = ast_metrics.get("quality_indicators", {})
            
            # Large class recommendations
            large_classes = quality_indicators.get("large_classes", [])
            if large_classes:
                recommendations.append({
                    "category": "Class Design",
                    "priority": "MEDIUM",
                    "issue": f"{filename} has {len(large_classes)} large classes",
                    "recommendation": "Consider splitting large classes using Single Responsibility Principle",
                    "impact": "Improves class cohesion and reduces coupling"
                })
            
            # Deep nesting recommendations
            deep_nesting = quality_indicators.get("deep_nesting", [])
            if deep_nesting:
                recommendations.append({
                    "category": "Code Structure",
                    "priority": "MEDIUM",
                    "issue": f"{filename} has functions with deep nesting (>4 levels)",
                    "recommendation": "Reduce nesting depth using early returns and guard clauses",
                    "impact": "Improves code readability and reduces complexity"
                })
        
        # Design pattern recommendations
        patterns_used = sum(1 for count in aggregate.get("design_patterns_usage", {}).values() if count > 0)
        if patterns_used < 2:
            recommendations.append({
                "category": "Design Patterns",
                "priority": "LOW",
                "issue": "Limited use of design patterns detected",
                "recommendation": "Consider implementing appropriate design patterns for better code organization",
                "impact": "Improves code structure and makes codebase more maintainable"
            })
        
        # Overall quality recommendations
        if assessment["overall_score"] < 60:
            recommendations.append({
                "category": "Overall Quality",
                "priority": "CRITICAL",
                "issue": f"Overall code quality is {assessment['quality_level']} ({assessment['overall_score']:.1f}/100)",
                "recommendation": "Prioritize code quality improvements before adding new features",
                "impact": "Essential for long-term project success and maintainability"
            })
        
        self.analysis_results["recommendations"] = recommendations
        
        # Print top recommendations
        print(f"   💡 Generated {len(recommendations)} quality recommendations")
        high_priority = [r for r in recommendations if r["priority"] in ["CRITICAL", "HIGH"]]
        if high_priority:
            print(f"   🚨 {len(high_priority)} high-priority items require attention")
    
    def _save_analysis_report(self):
        """Save comprehensive analysis report"""
        report_path = os.path.join(self.project_root, "validation", "comprehensive_phase1_code_quality_deep_report.json")
        
        # Ensure validation directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        # Save comprehensive report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2)
        
        print(f"\n📄 Comprehensive code quality report saved to: {report_path}")


def main():
    """Run Phase 1 Deep Code Quality Analysis"""
    try:
        print("StoryForge AI - Phase 1: Deep Code Quality Analysis")
        print("=" * 60)
        print("AST-based comprehensive code quality analysis with advanced metrics")
        print()
        
        analyzer = DeepCodeQualityAnalyzer()
        results = analyzer.run_deep_analysis()
        
        return results
        
    except Exception as e:
        print(f"❌ Deep code quality analysis error: {str(e)}")
        return None


if __name__ == "__main__":
    main()