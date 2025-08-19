#!/usr/bin/env python3
"""
StoryForge AI - Comprehensive Phase 1: Architecture Review & Code Quality Analysis
Advanced system architecture analysis with detailed component evaluation
"""

import json
import os
import sys
import ast
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import importlib.util

class ArchitectureAnalyzer:
    """Comprehensive architecture and code quality analysis"""
    
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.analysis_results = {
            "architecture_analysis": {},
            "code_quality_metrics": {},
            "dependency_analysis": {},
            "security_assessment": {},
            "performance_indicators": {},
            "maintainability_score": {},
            "timestamp": datetime.now().isoformat()
        }
    
    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Execute complete architecture and code quality analysis"""
        print("=== PHASE 1: COMPREHENSIVE ARCHITECTURE REVIEW ===\n")
        
        # 1. System Architecture Analysis
        print("🏗️ 1. Analyzing System Architecture...")
        self._analyze_system_architecture()
        
        # 2. Code Quality Assessment
        print("\n📊 2. Performing Code Quality Assessment...")
        self._analyze_code_quality()
        
        # 3. Dependency Analysis
        print("\n🔗 3. Analyzing Dependencies and Imports...")
        self._analyze_dependencies()
        
        # 4. Security Assessment
        print("\n🛡️ 4. Security Vulnerability Assessment...")
        self._analyze_security()
        
        # 5. Performance Indicators
        print("\n⚡ 5. Performance Architecture Analysis...")
        self._analyze_performance_architecture()
        
        # 6. Maintainability Assessment
        print("\n🔧 6. Maintainability and Technical Debt Analysis...")
        self._analyze_maintainability()
        
        # 7. Generate Comprehensive Report
        self._generate_architecture_report()
        
        return self.analysis_results
    
    def _analyze_system_architecture(self):
        """Analyze overall system architecture"""
        architecture = {
            "component_structure": self._analyze_components(),
            "data_flow_analysis": self._analyze_data_flows(),
            "api_design_analysis": self._analyze_api_design(),
            "integration_points": self._analyze_integration_points(),
            "architectural_patterns": self._identify_architectural_patterns()
        }
        
        self.analysis_results["architecture_analysis"] = architecture
        
        # Print key findings
        components = architecture["component_structure"]
        print(f"   📁 Components Found: {len(components['core_components'])} core, {len(components['utility_components'])} utility")
        print(f"   🔄 Data Flow Complexity: {architecture['data_flow_analysis']['complexity_score']}/100")
        print(f"   🎯 API Endpoints: {len(architecture['api_design_analysis']['endpoints'])} identified")
    
    def _analyze_components(self) -> Dict[str, Any]:
        """Analyze system components and their relationships"""
        core_components = []
        utility_components = []
        test_components = []
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Analyze file type and role
                if 'test' in py_file.name.lower() or py_file.name.startswith('test_'):
                    test_components.append({
                        "name": py_file.name,
                        "type": "test",
                        "size": len(content),
                        "classes": len(re.findall(r'class\s+\w+', content)),
                        "functions": len(re.findall(r'def\s+\w+', content))
                    })
                elif any(keyword in py_file.name.lower() for keyword in ['agent', 'director', 'chronicler', 'factory']):
                    core_components.append({
                        "name": py_file.name,
                        "type": "core",
                        "size": len(content),
                        "classes": len(re.findall(r'class\s+\w+', content)),
                        "functions": len(re.findall(r'def\s+\w+', content)),
                        "imports": len(re.findall(r'^(import|from)\s+', content, re.MULTILINE))
                    })
                else:
                    utility_components.append({
                        "name": py_file.name,
                        "type": "utility",
                        "size": len(content),
                        "classes": len(re.findall(r'class\s+\w+', content)),
                        "functions": len(re.findall(r'def\s+\w+', content))
                    })
                    
            except Exception as e:
                print(f"   ⚠️ Warning: Could not analyze {py_file.name}: {e}")
        
        return {
            "core_components": core_components,
            "utility_components": utility_components,
            "test_components": test_components,
            "total_files": len(python_files),
            "component_health": "good" if len(core_components) >= 3 else "needs_improvement"
        }
    
    def _analyze_data_flows(self) -> Dict[str, Any]:
        """Analyze data flow patterns and complexity"""
        data_flows = {
            "input_sources": [],
            "data_transformations": [],
            "output_destinations": [],
            "complexity_score": 0
        }
        
        # Analyze key files for data flow patterns
        key_files = ['director_agent.py', 'chronicler_agent.py', 'character_factory.py']
        
        total_complexity = 0
        files_analyzed = 0
        
        for filename in key_files:
            filepath = os.path.join(self.project_root, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Count data processing patterns
                    file_complexity = 0
                    file_complexity += len(re.findall(r'\.json|\.yaml|\.md', content)) * 2  # File I/O
                    file_complexity += len(re.findall(r'return\s+', content))  # Return statements
                    file_complexity += len(re.findall(r'def\s+\w+.*:', content))  # Function definitions
                    file_complexity += len(re.findall(r'class\s+\w+', content)) * 3  # Classes
                    
                    total_complexity += file_complexity
                    files_analyzed += 1
                    
                    # Identify specific flow patterns
                    if 'load' in content.lower() or 'read' in content.lower():
                        data_flows["input_sources"].append(filename)
                    if 'process' in content.lower() or 'transform' in content.lower():
                        data_flows["data_transformations"].append(filename)
                    if 'save' in content.lower() or 'write' in content.lower():
                        data_flows["output_destinations"].append(filename)
                        
                except Exception as e:
                    print(f"   ⚠️ Could not analyze data flows in {filename}: {e}")
        
        if files_analyzed > 0:
            data_flows["complexity_score"] = min(100, (total_complexity // files_analyzed) * 2)
        
        return data_flows
    
    def _analyze_api_design(self) -> Dict[str, Any]:
        """Analyze API design patterns and endpoints"""
        api_analysis = {
            "endpoints": [],
            "design_patterns": [],
            "error_handling": "unknown",
            "documentation_coverage": 0
        }
        
        # Look for API server file
        api_file = os.path.join(self.project_root, 'api_server.py')
        if os.path.exists(api_file):
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find API endpoints
                endpoints = re.findall(r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']', content)
                api_analysis["endpoints"] = [{"method": method, "path": path} for method, path in endpoints]
                
                # Check for design patterns
                if 'FastAPI' in content:
                    api_analysis["design_patterns"].append("FastAPI")
                if 'async def' in content:
                    api_analysis["design_patterns"].append("Async/Await")
                if 'HTTPException' in content:
                    api_analysis["error_handling"] = "structured"
                    api_analysis["design_patterns"].append("HTTP Exception Handling")
                
                # Check documentation coverage
                docstring_count = len(re.findall(r'""".*?"""', content, re.DOTALL))
                function_count = len(re.findall(r'def\s+\w+', content))
                if function_count > 0:
                    api_analysis["documentation_coverage"] = (docstring_count / function_count) * 100
                    
            except Exception as e:
                print(f"   ⚠️ Could not analyze API design: {e}")
        
        return api_analysis
    
    def _analyze_integration_points(self) -> Dict[str, Any]:
        """Analyze system integration points and external dependencies"""
        integration = {
            "file_system_integration": [],
            "configuration_integration": [],
            "external_libraries": [],
            "integration_complexity": "low"
        }
        
        all_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in all_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for file system integration
                if any(pattern in content for pattern in ['open(', 'Path(', 'os.path', 'pathlib']):
                    integration["file_system_integration"].append(py_file.name)
                
                # Check for configuration integration
                if any(pattern in content for pattern in ['config', 'yaml', 'json', 'ConfigLoader']):
                    integration["configuration_integration"].append(py_file.name)
                
                # Check for external library usage
                imports = re.findall(r'^from\s+(\w+)', content, re.MULTILINE)
                imports.extend(re.findall(r'^import\s+(\w+)', content, re.MULTILINE))
                
                external_libs = [imp for imp in imports if imp not in ['os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 're']]
                integration["external_libraries"].extend(external_libs)
                
            except Exception as e:
                continue
        
        # Remove duplicates and assess complexity
        integration["external_libraries"] = list(set(integration["external_libraries"]))
        
        total_integrations = (len(integration["file_system_integration"]) + 
                            len(integration["configuration_integration"]) + 
                            len(integration["external_libraries"]))
        
        if total_integrations > 15:
            integration["integration_complexity"] = "high"
        elif total_integrations > 8:
            integration["integration_complexity"] = "medium"
        else:
            integration["integration_complexity"] = "low"
        
        return integration
    
    def _identify_architectural_patterns(self) -> List[str]:
        """Identify architectural patterns used in the system"""
        patterns = []
        
        # Check for common patterns
        files_to_check = ['director_agent.py', 'character_factory.py', 'chronicler_agent.py']
        
        for filename in files_to_check:
            filepath = os.path.join(self.project_root, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Factory Pattern
                    if 'factory' in filename.lower() and 'create' in content.lower():
                        patterns.append("Factory Pattern")
                    
                    # Agent Pattern
                    if 'agent' in filename.lower() and 'class' in content:
                        patterns.append("Agent Pattern")
                    
                    # Singleton Pattern (basic check)
                    if '_instance' in content or '__new__' in content:
                        patterns.append("Singleton Pattern")
                    
                    # Observer Pattern
                    if 'register' in content and 'notify' in content:
                        patterns.append("Observer Pattern")
                    
                    # Strategy Pattern
                    if 'strategy' in content.lower() or ('execute' in content and 'algorithm' in content):
                        patterns.append("Strategy Pattern")
                        
                except Exception:
                    continue
        
        return list(set(patterns))
    
    def _analyze_code_quality(self):
        """Comprehensive code quality analysis"""
        quality_metrics = {
            "complexity_analysis": self._analyze_code_complexity(),
            "style_compliance": self._analyze_code_style(),
            "documentation_quality": self._analyze_documentation(),
            "error_handling_coverage": self._analyze_error_handling(),
            "test_coverage_estimate": self._estimate_test_coverage()
        }
        
        # Calculate overall quality score
        scores = []
        for metric_name, metric_data in quality_metrics.items():
            if isinstance(metric_data, dict) and 'score' in metric_data:
                scores.append(metric_data['score'])
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        quality_metrics["overall_quality_score"] = overall_score
        quality_metrics["quality_grade"] = self._calculate_grade(overall_score)
        
        self.analysis_results["code_quality_metrics"] = quality_metrics
        
        # Print summary
        print(f"   📊 Overall Code Quality: {overall_score:.1f}/100 (Grade: {quality_metrics['quality_grade']})")
        print(f"   🧮 Code Complexity: {quality_metrics['complexity_analysis']['average_complexity']:.1f}")
        print(f"   📝 Documentation Coverage: {quality_metrics['documentation_quality']['coverage_percentage']:.1f}%")
    
    def _analyze_code_complexity(self) -> Dict[str, Any]:
        """Analyze code complexity metrics"""
        complexity_data = {
            "files_analyzed": 0,
            "total_complexity": 0,
            "average_complexity": 0,
            "high_complexity_files": [],
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Calculate basic complexity metrics
                file_complexity = 0
                file_complexity += len(re.findall(r'\bif\b', content))  # Conditional statements
                file_complexity += len(re.findall(r'\bfor\b|\bwhile\b', content))  # Loops
                file_complexity += len(re.findall(r'\btry\b', content))  # Exception handling
                file_complexity += len(re.findall(r'\bdef\s+\w+', content))  # Functions
                file_complexity += len(re.findall(r'\bclass\s+\w+', content)) * 2  # Classes
                
                complexity_data["files_analyzed"] += 1
                complexity_data["total_complexity"] += file_complexity
                
                if file_complexity > 50:  # High complexity threshold
                    complexity_data["high_complexity_files"].append({
                        "file": py_file.name,
                        "complexity": file_complexity
                    })
                    
            except Exception:
                continue
        
        if complexity_data["files_analyzed"] > 0:
            complexity_data["average_complexity"] = complexity_data["total_complexity"] / complexity_data["files_analyzed"]
            
            # Score: Lower complexity is better
            if complexity_data["average_complexity"] < 20:
                complexity_data["score"] = 90
            elif complexity_data["average_complexity"] < 40:
                complexity_data["score"] = 70
            elif complexity_data["average_complexity"] < 60:
                complexity_data["score"] = 50
            else:
                complexity_data["score"] = 30
        
        return complexity_data
    
    def _analyze_code_style(self) -> Dict[str, Any]:
        """Analyze code style and formatting"""
        style_data = {
            "naming_convention_score": 0,
            "formatting_score": 0,
            "import_organization_score": 0,
            "score": 0,
            "style_issues": []
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        total_files = len(python_files)
        
        if total_files == 0:
            return style_data
        
        good_naming_files = 0
        good_formatting_files = 0
        good_imports_files = 0
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check naming conventions
                classes = re.findall(r'class\s+(\w+)', content)
                functions = re.findall(r'def\s+(\w+)', content)
                
                good_naming = True
                for cls_name in classes:
                    if not cls_name[0].isupper():  # PascalCase for classes
                        good_naming = False
                        break
                
                for func_name in functions:
                    if not func_name.islower() and '_' not in func_name:  # snake_case for functions
                        if not func_name.startswith('__'):  # Allow special methods
                            good_naming = False
                            break
                
                if good_naming:
                    good_naming_files += 1
                
                # Check basic formatting
                lines = content.split('\n')
                long_lines = [line for line in lines if len(line) > 120]
                if len(long_lines) / len(lines) < 0.1:  # Less than 10% long lines
                    good_formatting_files += 1
                
                # Check import organization
                import_lines = [line for line in lines if line.strip().startswith(('import ', 'from '))]
                if import_lines:
                    # Check if imports are at the top (within first 20% of file)
                    first_import_line = next((i for i, line in enumerate(lines) if line.strip().startswith(('import ', 'from '))), 0)
                    if first_import_line < len(lines) * 0.2:
                        good_imports_files += 1
                        
            except Exception:
                continue
        
        # Calculate scores
        style_data["naming_convention_score"] = (good_naming_files / total_files) * 100
        style_data["formatting_score"] = (good_formatting_files / total_files) * 100
        style_data["import_organization_score"] = (good_imports_files / total_files) * 100
        
        style_data["score"] = (style_data["naming_convention_score"] + 
                              style_data["formatting_score"] + 
                              style_data["import_organization_score"]) / 3
        
        return style_data
    
    def _analyze_documentation(self) -> Dict[str, Any]:
        """Analyze documentation quality and coverage"""
        doc_data = {
            "files_with_docstrings": 0,
            "functions_with_docstrings": 0,
            "total_functions": 0,
            "classes_with_docstrings": 0,
            "total_classes": 0,
            "coverage_percentage": 0,
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for file-level docstrings
                if content.strip().startswith('"""') or content.strip().startswith("'''"):
                    doc_data["files_with_docstrings"] += 1
                
                # Find all functions and their documentation
                function_matches = re.finditer(r'def\s+(\w+)\s*\([^)]*\):', content)
                for match in function_matches:
                    doc_data["total_functions"] += 1
                    
                    # Look for docstring after function definition
                    func_start = match.end()
                    remaining_content = content[func_start:]
                    
                    # Simple check for docstring presence
                    if remaining_content.lstrip().startswith('"""') or remaining_content.lstrip().startswith("'''"):
                        doc_data["functions_with_docstrings"] += 1
                
                # Find all classes and their documentation
                class_matches = re.finditer(r'class\s+(\w+)', content)
                for match in class_matches:
                    doc_data["total_classes"] += 1
                    
                    # Look for docstring after class definition
                    class_start = match.end()
                    remaining_content = content[class_start:]
                    
                    if remaining_content.lstrip().startswith('"""') or remaining_content.lstrip().startswith("'''"):
                        doc_data["classes_with_docstrings"] += 1
                        
            except Exception:
                continue
        
        # Calculate coverage
        total_items = doc_data["total_functions"] + doc_data["total_classes"]
        documented_items = doc_data["functions_with_docstrings"] + doc_data["classes_with_docstrings"]
        
        if total_items > 0:
            doc_data["coverage_percentage"] = (documented_items / total_items) * 100
            doc_data["score"] = doc_data["coverage_percentage"]
        
        return doc_data
    
    def _analyze_error_handling(self) -> Dict[str, Any]:
        """Analyze error handling patterns and coverage"""
        error_data = {
            "files_with_error_handling": 0,
            "total_try_blocks": 0,
            "specific_exceptions": 0,
            "generic_exceptions": 0,
            "error_handling_score": 0,
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        total_files = len(python_files)
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try_blocks = re.findall(r'\btry\s*:', content)
                if try_blocks:
                    error_data["files_with_error_handling"] += 1
                    error_data["total_try_blocks"] += len(try_blocks)
                
                # Check for specific vs generic exception handling
                specific_except = re.findall(r'except\s+\w+Error', content)
                generic_except = re.findall(r'except\s*:', content)
                
                error_data["specific_exceptions"] += len(specific_except)
                error_data["generic_exceptions"] += len(generic_except)
                
            except Exception:
                continue
        
        # Calculate error handling score
        if total_files > 0:
            coverage_score = (error_data["files_with_error_handling"] / total_files) * 100
            
            # Bonus for specific exception handling
            total_exceptions = error_data["specific_exceptions"] + error_data["generic_exceptions"]
            if total_exceptions > 0:
                specificity_bonus = (error_data["specific_exceptions"] / total_exceptions) * 20
            else:
                specificity_bonus = 0
            
            error_data["error_handling_score"] = min(100, coverage_score + specificity_bonus)
            error_data["score"] = error_data["error_handling_score"]
        
        return error_data
    
    def _estimate_test_coverage(self) -> Dict[str, Any]:
        """Estimate test coverage based on available test files"""
        test_data = {
            "test_files_found": 0,
            "test_functions": 0,
            "source_files": 0,
            "estimated_coverage": 0,
            "score": 0
        }
        
        # Count test files
        test_files = list(Path(self.project_root).glob("*test*.py"))
        test_data["test_files_found"] = len(test_files)
        
        # Count test functions
        for test_file in test_files:
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                test_functions = re.findall(r'def\s+test_\w+', content)
                test_data["test_functions"] += len(test_functions)
            except Exception:
                continue
        
        # Count source files (non-test Python files)
        all_py_files = list(Path(self.project_root).glob("*.py"))
        source_files = [f for f in all_py_files if 'test' not in f.name.lower()]
        test_data["source_files"] = len(source_files)
        
        # Estimate coverage
        if test_data["source_files"] > 0:
            test_ratio = test_data["test_files_found"] / test_data["source_files"]
            function_ratio = test_data["test_functions"] / max(1, test_data["source_files"] * 5)  # Assume 5 functions per file
            
            test_data["estimated_coverage"] = min(100, (test_ratio * 50) + (function_ratio * 50))
            test_data["score"] = test_data["estimated_coverage"]
        
        return test_data
    
    def _calculate_grade(self, score: float) -> str:
        """Convert numerical score to letter grade"""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _analyze_dependencies(self):
        """Analyze dependency structure and potential issues"""
        dependencies = {
            "external_dependencies": self._get_external_dependencies(),
            "internal_dependencies": self._get_internal_dependencies(),
            "circular_dependencies": self._detect_circular_dependencies(),
            "dependency_health": "unknown"
        }
        
        self.analysis_results["dependency_analysis"] = dependencies
        
        # Assess dependency health
        external_count = len(dependencies["external_dependencies"])
        circular_count = len(dependencies["circular_dependencies"])
        
        if circular_count > 0:
            dependencies["dependency_health"] = "poor"
        elif external_count > 20:
            dependencies["dependency_health"] = "concerning"
        elif external_count > 10:
            dependencies["dependency_health"] = "moderate"
        else:
            dependencies["dependency_health"] = "good"
        
        print(f"   📦 External Dependencies: {external_count}")
        print(f"   🔄 Circular Dependencies: {circular_count}")
        print(f"   💊 Dependency Health: {dependencies['dependency_health']}")
    
    def _get_external_dependencies(self) -> List[str]:
        """Get list of external dependencies"""
        external_deps = set()
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract imports
                imports = re.findall(r'^(?:from\s+(\w+)|import\s+(\w+))', content, re.MULTILINE)
                for imp_tuple in imports:
                    imp = imp_tuple[0] or imp_tuple[1]
                    
                    # Filter out standard library and local imports
                    if imp not in ['os', 'sys', 'json', 'datetime', 'pathlib', 'typing', 're', 'logging', 'time', 'tempfile']:
                        # Check if it's not a local import
                        local_file = os.path.join(self.project_root, f"{imp}.py")
                        if not os.path.exists(local_file):
                            external_deps.add(imp)
                            
            except Exception:
                continue
        
        return list(external_deps)
    
    def _get_internal_dependencies(self) -> Dict[str, List[str]]:
        """Get internal dependency mapping"""
        internal_deps = {}
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            file_deps = []
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find local imports
                imports = re.findall(r'^(?:from\s+(\w+)|import\s+(\w+))', content, re.MULTILINE)
                for imp_tuple in imports:
                    imp = imp_tuple[0] or imp_tuple[1]
                    
                    # Check if it's a local file
                    local_file = os.path.join(self.project_root, f"{imp}.py")
                    if os.path.exists(local_file):
                        file_deps.append(imp)
                
                internal_deps[py_file.stem] = file_deps
                
            except Exception:
                internal_deps[py_file.stem] = []
        
        return internal_deps
    
    def _detect_circular_dependencies(self) -> List[str]:
        """Detect circular dependency patterns"""
        # This is a simplified circular dependency detection
        # In a real implementation, you'd use graph algorithms
        circular_deps = []
        
        internal_deps = self._get_internal_dependencies()
        
        for file_a, deps_a in internal_deps.items():
            for dep in deps_a:
                if dep in internal_deps:
                    # Check if dep imports file_a back
                    if file_a in internal_deps[dep]:
                        circular_deps.append(f"{file_a} <-> {dep}")
        
        return list(set(circular_deps))
    
    def _analyze_security(self):
        """Security vulnerability assessment"""
        security = {
            "potential_vulnerabilities": self._scan_security_patterns(),
            "input_validation": self._check_input_validation(),
            "file_operations": self._check_file_operations(),
            "security_score": 0
        }
        
        # Calculate security score
        vuln_count = len(security["potential_vulnerabilities"])
        input_val_score = security["input_validation"]["score"]
        file_ops_score = security["file_operations"]["score"]
        
        security["security_score"] = max(0, 100 - (vuln_count * 10) + (input_val_score + file_ops_score) / 2)
        
        self.analysis_results["security_assessment"] = security
        
        print(f"   🛡️ Potential Vulnerabilities: {vuln_count}")
        print(f"   🔐 Security Score: {security['security_score']:.1f}/100")
    
    def _scan_security_patterns(self) -> List[Dict[str, str]]:
        """Scan for potential security vulnerability patterns"""
        vulnerabilities = []
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for potential security issues
                if re.search(r'eval\s*\(', content):
                    vulnerabilities.append({
                        "file": py_file.name,
                        "type": "Code Injection",
                        "pattern": "eval() usage"
                    })
                
                if re.search(r'exec\s*\(', content):
                    vulnerabilities.append({
                        "file": py_file.name,
                        "type": "Code Injection",
                        "pattern": "exec() usage"
                    })
                
                if re.search(r'shell=True', content):
                    vulnerabilities.append({
                        "file": py_file.name,
                        "type": "Command Injection",
                        "pattern": "shell=True in subprocess"
                    })
                
                if re.search(r'password.*=.*["\'][^"\']*["\']', content, re.IGNORECASE):
                    vulnerabilities.append({
                        "file": py_file.name,
                        "type": "Hardcoded Credentials",
                        "pattern": "Hardcoded password"
                    })
                    
            except Exception:
                continue
        
        return vulnerabilities
    
    def _check_input_validation(self) -> Dict[str, Any]:
        """Check for input validation patterns"""
        validation_data = {
            "validation_functions": 0,
            "sanitization_patterns": 0,
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for validation patterns
                if re.search(r'validate|check|verify', content, re.IGNORECASE):
                    validation_data["validation_functions"] += 1
                
                # Look for sanitization patterns
                if re.search(r'sanitize|clean|escape|strip', content, re.IGNORECASE):
                    validation_data["sanitization_patterns"] += 1
                    
            except Exception:
                continue
        
        total_patterns = validation_data["validation_functions"] + validation_data["sanitization_patterns"]
        validation_data["score"] = min(100, total_patterns * 10)
        
        return validation_data
    
    def _check_file_operations(self) -> Dict[str, Any]:
        """Check file operation security"""
        file_ops_data = {
            "safe_file_operations": 0,
            "potentially_unsafe_operations": 0,
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for safe file operations
                if re.search(r'with\s+open\s*\(', content):
                    file_ops_data["safe_file_operations"] += len(re.findall(r'with\s+open\s*\(', content))
                
                # Look for potentially unsafe operations
                if re.search(r'open\s*\([^)]*\)', content) and not re.search(r'with\s+open\s*\(', content):
                    file_ops_data["potentially_unsafe_operations"] += len(re.findall(r'(?<!with\s)open\s*\(', content))
                    
            except Exception:
                continue
        
        total_ops = file_ops_data["safe_file_operations"] + file_ops_data["potentially_unsafe_operations"]
        if total_ops > 0:
            safety_ratio = file_ops_data["safe_file_operations"] / total_ops
            file_ops_data["score"] = safety_ratio * 100
        else:
            file_ops_data["score"] = 100  # No file operations found
        
        return file_ops_data
    
    def _analyze_performance_architecture(self):
        """Analyze architecture from performance perspective"""
        performance = {
            "async_usage": self._check_async_patterns(),
            "caching_patterns": self._check_caching_patterns(),
            "resource_management": self._check_resource_management(),
            "performance_score": 0
        }
        
        # Calculate performance score
        scores = []
        for key, value in performance.items():
            if isinstance(value, dict) and 'score' in value:
                scores.append(value['score'])
        
        if scores:
            performance["performance_score"] = sum(scores) / len(scores)
        
        self.analysis_results["performance_indicators"] = performance
        
        print(f"   ⚡ Performance Score: {performance['performance_score']:.1f}/100")
        print(f"   🔄 Async Patterns: {performance['async_usage']['async_functions']} found")
    
    def _check_async_patterns(self) -> Dict[str, Any]:
        """Check for async/await usage patterns"""
        async_data = {
            "async_functions": 0,
            "await_usage": 0,
            "async_score": 0,
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                async_functions = re.findall(r'async\s+def\s+\w+', content)
                await_calls = re.findall(r'\bawait\s+', content)
                
                async_data["async_functions"] += len(async_functions)
                async_data["await_usage"] += len(await_calls)
                
            except Exception:
                continue
        
        # Score based on modern async usage
        if async_data["async_functions"] > 0:
            async_data["score"] = min(100, async_data["async_functions"] * 20)
        else:
            async_data["score"] = 60  # Neutral score for sync code
        
        return async_data
    
    def _check_caching_patterns(self) -> Dict[str, Any]:
        """Check for caching implementation patterns"""
        caching_data = {
            "caching_implementations": 0,
            "cache_libraries": [],
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for caching patterns
                if re.search(r'cache|Cache|lru_cache', content):
                    caching_data["caching_implementations"] += 1
                
                # Check for cache libraries
                if 'functools' in content and 'lru_cache' in content:
                    caching_data["cache_libraries"].append("functools.lru_cache")
                    
            except Exception:
                continue
        
        caching_data["score"] = min(100, caching_data["caching_implementations"] * 25)
        
        return caching_data
    
    def _check_resource_management(self) -> Dict[str, Any]:
        """Check resource management patterns"""
        resource_data = {
            "context_managers": 0,
            "proper_cleanup": 0,
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for context managers
                context_managers = re.findall(r'with\s+\w+', content)
                resource_data["context_managers"] += len(context_managers)
                
                # Check for cleanup patterns
                if re.search(r'finally:|__exit__|cleanup', content):
                    resource_data["proper_cleanup"] += 1
                    
            except Exception:
                continue
        
        # Score based on resource management practices
        total_score = (resource_data["context_managers"] * 5) + (resource_data["proper_cleanup"] * 20)
        resource_data["score"] = min(100, total_score)
        
        return resource_data
    
    def _analyze_maintainability(self):
        """Analyze code maintainability and technical debt"""
        maintainability = {
            "technical_debt_indicators": self._find_technical_debt(),
            "code_duplication": self._estimate_code_duplication(),
            "modularity_score": self._assess_modularity(),
            "maintainability_score": 0
        }
        
        # Calculate maintainability score
        debt_penalty = len(maintainability["technical_debt_indicators"]) * 5
        duplication_penalty = maintainability["code_duplication"]["estimated_duplication"] * 2
        modularity_bonus = maintainability["modularity_score"]["score"]
        
        maintainability["maintainability_score"] = max(0, 100 - debt_penalty - duplication_penalty + (modularity_bonus - 50))
        
        self.analysis_results["maintainability_score"] = maintainability
        
        print(f"   🔧 Technical Debt Items: {len(maintainability['technical_debt_indicators'])}")
        print(f"   📊 Maintainability Score: {maintainability['maintainability_score']:.1f}/100")
    
    def _find_technical_debt(self) -> List[Dict[str, str]]:
        """Find technical debt indicators in code"""
        debt_indicators = []
        
        # Common debt indicators
        debt_patterns = [
            (r'TODO|FIXME|HACK|XXX', "Technical Debt Comment"),
            (r'#\s*temp|#\s*temporary', "Temporary Code"),
            (r'#\s*remove|#\s*delete', "Code Marked for Removal"),
            (r'pass\s*#|pass\s*$', "Empty Implementation")
        ]
        
        python_files = list(Path(self.project_root).glob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                for pattern, debt_type in debt_patterns:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        debt_indicators.append({
                            "file": py_file.name,
                            "type": debt_type,
                            "location": f"Line {content[:match.start()].count(chr(10)) + 1}",
                            "snippet": content[match.start():match.end()]
                        })
                        
            except Exception:
                continue
        
        return debt_indicators
    
    def _estimate_code_duplication(self) -> Dict[str, Any]:
        """Estimate code duplication levels"""
        duplication_data = {
            "function_signatures": [],
            "similar_blocks": 0,
            "estimated_duplication": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        all_functions = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                functions = re.findall(r'def\s+(\w+)\s*\([^)]*\):', content)
                all_functions.extend(functions)
                
            except Exception:
                continue
        
        # Simple duplication check based on function names
        function_counts = {}
        for func in all_functions:
            function_counts[func] = function_counts.get(func, 0) + 1
        
        duplicated_functions = {func: count for func, count in function_counts.items() if count > 1}
        
        if all_functions:
            duplication_data["estimated_duplication"] = len(duplicated_functions) / len(all_functions) * 100
        
        duplication_data["function_signatures"] = list(duplicated_functions.keys())
        
        return duplication_data
    
    def _assess_modularity(self) -> Dict[str, Any]:
        """Assess code modularity and separation of concerns"""
        modularity_data = {
            "average_file_size": 0,
            "function_count_distribution": {},
            "class_count_distribution": {},
            "score": 0
        }
        
        python_files = list(Path(self.project_root).glob("*.py"))
        file_sizes = []
        file_functions = []
        file_classes = []
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_sizes.append(len(content))
                
                functions = len(re.findall(r'def\s+\w+', content))
                classes = len(re.findall(r'class\s+\w+', content))
                
                file_functions.append(functions)
                file_classes.append(classes)
                
            except Exception:
                continue
        
        if file_sizes:
            modularity_data["average_file_size"] = sum(file_sizes) / len(file_sizes)
            
            # Score based on reasonable file sizes and function distribution
            avg_functions = sum(file_functions) / len(file_functions)
            avg_classes = sum(file_classes) / len(file_classes)
            
            # Good modularity: moderate file sizes, reasonable function/class counts
            size_score = 100 - max(0, (modularity_data["average_file_size"] - 2000) / 100)  # Penalty for large files
            function_score = 100 - max(0, (avg_functions - 10) * 5)  # Penalty for too many functions per file
            class_score = 100 - max(0, (avg_classes - 3) * 10)  # Penalty for too many classes per file
            
            modularity_data["score"] = (size_score + function_score + class_score) / 3
        
        return modularity_data
    
    def _generate_architecture_report(self):
        """Generate comprehensive architecture analysis report"""
        report_path = os.path.join(self.project_root, "validation", "comprehensive_phase1_architecture_report.json")
        
        # Ensure validation directory exists
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        # Add executive summary
        executive_summary = {
            "analysis_date": datetime.now().isoformat(),
            "overall_architecture_health": self._calculate_overall_health(),
            "critical_issues": self._identify_critical_issues(),
            "recommendations": self._generate_recommendations()
        }
        
        self.analysis_results["executive_summary"] = executive_summary
        
        # Save comprehensive report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2)
        
        # Print executive summary
        print(f"\n=== PHASE 1 ARCHITECTURE SUMMARY ===")
        print(f"🏗️ Overall Architecture Health: {executive_summary['overall_architecture_health']}")
        print(f"🚨 Critical Issues: {len(executive_summary['critical_issues'])}")
        print(f"💡 Recommendations: {len(executive_summary['recommendations'])}")
        print(f"📄 Detailed report saved to: {report_path}")
    
    def _calculate_overall_health(self) -> str:
        """Calculate overall architecture health rating"""
        scores = []
        
        # Collect all available scores
        if "code_quality_metrics" in self.analysis_results:
            scores.append(self.analysis_results["code_quality_metrics"].get("overall_quality_score", 0))
        
        if "security_assessment" in self.analysis_results:
            scores.append(self.analysis_results["security_assessment"].get("security_score", 0))
        
        if "performance_indicators" in self.analysis_results:
            scores.append(self.analysis_results["performance_indicators"].get("performance_score", 0))
        
        if "maintainability_score" in self.analysis_results:
            scores.append(self.analysis_results["maintainability_score"].get("maintainability_score", 0))
        
        if scores:
            avg_score = sum(scores) / len(scores)
            if avg_score >= 80:
                return "EXCELLENT"
            elif avg_score >= 70:
                return "GOOD"
            elif avg_score >= 60:
                return "ACCEPTABLE"
            elif avg_score >= 40:
                return "NEEDS IMPROVEMENT"
            else:
                return "CRITICAL"
        
        return "UNKNOWN"
    
    def _identify_critical_issues(self) -> List[str]:
        """Identify critical architectural issues"""
        critical_issues = []
        
        # Check code quality
        if "code_quality_metrics" in self.analysis_results:
            quality = self.analysis_results["code_quality_metrics"]
            if quality.get("overall_quality_score", 0) < 60:
                critical_issues.append("Overall code quality below acceptable standards")
        
        # Check security
        if "security_assessment" in self.analysis_results:
            security = self.analysis_results["security_assessment"]
            if len(security.get("potential_vulnerabilities", [])) > 0:
                critical_issues.append("Security vulnerabilities detected")
        
        # Check dependencies
        if "dependency_analysis" in self.analysis_results:
            deps = self.analysis_results["dependency_analysis"]
            if len(deps.get("circular_dependencies", [])) > 0:
                critical_issues.append("Circular dependencies detected")
        
        # Check maintainability
        if "maintainability_score" in self.analysis_results:
            maint = self.analysis_results["maintainability_score"]
            if maint.get("maintainability_score", 0) < 50:
                critical_issues.append("Low maintainability score indicates high technical debt")
        
        return critical_issues
    
    def _generate_recommendations(self) -> List[str]:
        """Generate architecture improvement recommendations"""
        recommendations = []
        
        # Code quality recommendations
        if "code_quality_metrics" in self.analysis_results:
            quality = self.analysis_results["code_quality_metrics"]
            if quality.get("documentation_quality", {}).get("coverage_percentage", 0) < 70:
                recommendations.append("Improve documentation coverage - aim for 80%+ docstring coverage")
            
            if quality.get("complexity_analysis", {}).get("average_complexity", 0) > 40:
                recommendations.append("Reduce code complexity - consider refactoring complex functions")
        
        # Security recommendations
        if "security_assessment" in self.analysis_results:
            security = self.analysis_results["security_assessment"]
            if security.get("security_score", 0) < 80:
                recommendations.append("Enhance security measures - review input validation and error handling")
        
        # Performance recommendations
        if "performance_indicators" in self.analysis_results:
            perf = self.analysis_results["performance_indicators"]
            if perf.get("async_usage", {}).get("async_functions", 0) == 0:
                recommendations.append("Consider async/await patterns for I/O operations to improve performance")
        
        # Maintainability recommendations
        if "maintainability_score" in self.analysis_results:
            maint = self.analysis_results["maintainability_score"]
            debt_count = len(maint.get("technical_debt_indicators", []))
            if debt_count > 5:
                recommendations.append(f"Address technical debt - {debt_count} items identified for cleanup")
        
        return recommendations


def main():
    """Run Phase 1 Comprehensive Architecture Review"""
    try:
        print("StoryForge AI - Phase 1: Comprehensive Architecture Review & Code Quality Analysis")
        print("=" * 80)
        print("Advanced system architecture analysis with detailed component evaluation")
        print()
        
        analyzer = ArchitectureAnalyzer()
        results = analyzer.run_comprehensive_analysis()
        
        return results
        
    except Exception as e:
        print(f"❌ Architecture analysis error: {str(e)}")
        return None


if __name__ == "__main__":
    main()