#!/usr/bin/env python3
"""
CODE QUALITY MONITORING SYSTEM
====================================

Real-time code quality monitoring with automated analysis,
technical debt tracking, and continuous improvement suggestions.

Features:
- Continuous code quality monitoring
- Technical debt tracking and prioritization
- Automated code review and suggestions
- Quality trend analysis
- Refactoring recommendations
- Complexity analysis and reporting
"""

import ast
import logging
import time
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from pathlib import Path
import re
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QualityMetric(str, Enum):
    """Code quality metric types"""
    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"
    READABILITY = "readability"
    TESTABILITY = "testability"
    DUPLICATION = "duplication"
    COUPLING = "coupling"
    COHESION = "cohesion"
    TECHNICAL_DEBT = "technical_debt"

class Severity(str, Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

@dataclass
class QualityIssue:
    """Code quality issue"""
    file_path: str
    line_number: int
    metric: QualityMetric
    severity: Severity
    message: str
    suggestion: Optional[str] = None
    complexity_score: Optional[float] = None
    debt_minutes: Optional[int] = None
    rule_id: Optional[str] = None
    
    @property
    def issue_id(self) -> str:
        """Generate unique issue ID"""
        content = f"{self.file_path}:{self.line_number}:{self.rule_id}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

@dataclass
class FileQualityReport:
    """Quality report for a single file"""
    file_path: str
    lines_of_code: int
    complexity_score: float
    maintainability_index: float
    duplication_percentage: float
    test_coverage: float
    issues: List[QualityIssue] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.now)
    
    @property
    def technical_debt_minutes(self) -> int:
        """Calculate total technical debt in minutes"""
        return sum(issue.debt_minutes or 0 for issue in self.issues)
    
    @property
    def critical_issues_count(self) -> int:
        """Count critical issues"""
        return len([i for i in self.issues if i.severity == Severity.CRITICAL])
    
    @property
    def quality_grade(self) -> str:
        """Calculate overall quality grade"""
        score = (
            self.maintainability_index * 0.4 +
            (100 - self.complexity_score) * 0.3 +
            self.test_coverage * 0.2 +
            (100 - self.duplication_percentage) * 0.1
        )
        
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

@dataclass
class ProjectQualityReport:
    """Overall project quality report"""
    project_name: str
    total_files: int
    total_lines_of_code: int
    average_complexity: float
    average_maintainability: float
    overall_coverage: float
    technical_debt_hours: float
    file_reports: Dict[str, FileQualityReport] = field(default_factory=dict)
    trends: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def quality_distribution(self) -> Dict[str, int]:
        """Get distribution of quality grades"""
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for report in self.file_reports.values():
            distribution[report.quality_grade] += 1
        return distribution
    
    @property
    def total_issues(self) -> int:
        """Get total number of issues"""
        return sum(len(report.issues) for report in self.file_reports.values())

class ComplexityAnalyzer(ast.NodeVisitor):
    """AST-based complexity analyzer"""
    
    def __init__(self):
        self.complexity = 0
        self.functions = []
        self.classes = []
        self.current_function = None
        self.current_class = None
    
    def visit_FunctionDef(self, node):
        """Analyze function complexity"""
        self.current_function = {
            "name": node.name,
            "line": node.lineno,
            "complexity": 1,  # Base complexity
            "parameters": len(node.args.args),
            "nested_functions": 0
        }
        
        # Count complexity contributors
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                self.current_function["complexity"] += 1
            elif isinstance(child, ast.BoolOp):
                self.current_function["complexity"] += len(child.values) - 1
        
        self.functions.append(self.current_function)
        self.complexity += self.current_function["complexity"]
        self.generic_visit(node)
    
    def visit_ClassDef(self, node):
        """Analyze class complexity"""
        self.current_class = {
            "name": node.name,
            "line": node.lineno,
            "methods": 0,
            "complexity": 0
        }
        
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self.current_class["methods"] += 1
        
        self.classes.append(self.current_class)
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Count conditional complexity"""
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Count loop complexity"""
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Count loop complexity"""
        self.complexity += 1
        self.generic_visit(node)

class DuplicationDetector:
    """Code duplication detection"""
    
    def __init__(self, min_lines: int = 6):
        self.min_lines = min_lines
        self.code_blocks = {}
        self.duplications = []
    
    def analyze_file(self, file_path: str, content: str) -> float:
        """Analyze file for code duplication"""
        lines = content.strip().split('\n')
        
        # Extract code blocks
        for i in range(len(lines) - self.min_lines + 1):
            block = '\n'.join(lines[i:i + self.min_lines])
            normalized_block = self._normalize_code(block)
            
            if normalized_block in self.code_blocks:
                self.code_blocks[normalized_block].append((file_path, i + 1))
            else:
                self.code_blocks[normalized_block] = [(file_path, i + 1)]
        
        # Calculate duplication percentage
        duplicated_lines = 0
        for block, locations in self.code_blocks.items():
            if len(locations) > 1:
                duplicated_lines += self.min_lines * (len(locations) - 1)
        
        return min((duplicated_lines / len(lines)) * 100, 100) if lines else 0
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison"""
        # Remove comments and normalize whitespace
        normalized = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

class TechnicalDebtCalculator:
    """Technical debt calculation and tracking"""
    
    def __init__(self):
        self.debt_rules = {
            "high_complexity": {"threshold": 10, "minutes_per_point": 15},
            "long_method": {"threshold": 50, "minutes": 30},
            "large_class": {"threshold": 500, "minutes": 60},
            "deep_nesting": {"threshold": 4, "minutes": 20},
            "code_duplication": {"threshold": 10, "minutes_per_percent": 5},
            "no_tests": {"minutes": 120},
            "poor_naming": {"minutes": 10},
            "magic_numbers": {"minutes": 5},
        }
    
    def calculate_debt(self, quality_report: FileQualityReport) -> int:
        """Calculate technical debt for a file in minutes"""
        total_debt = 0
        
        # Complexity debt
        if quality_report.complexity_score > self.debt_rules["high_complexity"]["threshold"]:
            excess_complexity = quality_report.complexity_score - self.debt_rules["high_complexity"]["threshold"]
            total_debt += excess_complexity * self.debt_rules["high_complexity"]["minutes_per_point"]
        
        # Size debt
        if quality_report.lines_of_code > self.debt_rules["long_method"]["threshold"]:
            total_debt += self.debt_rules["long_method"]["minutes"]
        
        if quality_report.lines_of_code > self.debt_rules["large_class"]["threshold"]:
            total_debt += self.debt_rules["large_class"]["minutes"]
        
        # Duplication debt
        if quality_report.duplication_percentage > self.debt_rules["code_duplication"]["threshold"]:
            total_debt += quality_report.duplication_percentage * self.debt_rules["code_duplication"]["minutes_per_percent"]
        
        # Test coverage debt
        if quality_report.test_coverage < 80:
            coverage_deficit = 80 - quality_report.test_coverage
            total_debt += (coverage_deficit / 100) * self.debt_rules["no_tests"]["minutes"]
        
        return int(total_debt)

class QualityMonitor:
    """
    Main code quality monitoring system
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.complexity_analyzer = ComplexityAnalyzer()
        self.duplication_detector = DuplicationDetector()
        self.debt_calculator = TechnicalDebtCalculator()
        self.quality_history = []
        
        # Quality thresholds
        self.thresholds = {
            "complexity": {"warning": 10, "critical": 20},
            "maintainability": {"warning": 60, "critical": 40},
            "duplication": {"warning": 10, "critical": 20},
            "coverage": {"warning": 70, "critical": 50}
        }
    
    async def analyze_project(self, file_patterns: List[str] = None) -> ProjectQualityReport:
        """Analyze entire project quality"""
        file_patterns = file_patterns or ["**/*.py"]
        
        logger.info("Starting comprehensive project quality analysis")
        
        # Find all Python files
        python_files = []
        for pattern in file_patterns:
            python_files.extend(self.project_root.glob(pattern))
        
        # Filter out test files and migrations for main analysis
        source_files = [
            f for f in python_files 
            if not any(part.startswith(('test_', '__pycache__', '.pytest_cache')) 
                      for part in f.parts)
        ]
        
        # Analyze each file
        file_reports = {}
        total_loc = 0
        total_complexity = 0
        total_debt_minutes = 0
        
        for file_path in source_files:
            try:
                report = await self._analyze_file(file_path)
                if report:
                    file_reports[str(file_path)] = report
                    total_loc += report.lines_of_code
                    total_complexity += report.complexity_score
                    total_debt_minutes += report.technical_debt_minutes
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
        
        # Calculate project-level metrics
        avg_complexity = total_complexity / len(file_reports) if file_reports else 0
        avg_maintainability = sum(r.maintainability_index for r in file_reports.values()) / len(file_reports) if file_reports else 0
        overall_coverage = sum(r.test_coverage for r in file_reports.values()) / len(file_reports) if file_reports else 0
        
        # Create project report
        project_report = ProjectQualityReport(
            project_name=self.project_root.name,
            total_files=len(file_reports),
            total_lines_of_code=total_loc,
            average_complexity=avg_complexity,
            average_maintainability=avg_maintainability,
            overall_coverage=overall_coverage,
            technical_debt_hours=total_debt_minutes / 60,
            file_reports=file_reports
        )
        
        # Store in history for trend analysis
        self.quality_history.append({
            "timestamp": datetime.now().isoformat(),
            "complexity": avg_complexity,
            "maintainability": avg_maintainability,
            "coverage": overall_coverage,
            "debt_hours": total_debt_minutes / 60,
            "total_issues": project_report.total_issues
        })
        
        logger.info(f"Project analysis complete: {len(file_reports)} files analyzed")
        
        return project_report
    
    async def _analyze_file(self, file_path: Path) -> Optional[FileQualityReport]:
        """Analyze a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                return None
            
            # Parse AST for complexity analysis
            try:
                tree = ast.parse(content)
                self.complexity_analyzer = ComplexityAnalyzer()
                self.complexity_analyzer.visit(tree)
            except SyntaxError:
                logger.warning(f"Syntax error in {file_path}, skipping analysis")
                return None
            
            # Calculate metrics
            lines = content.split('\n')
            loc = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            
            complexity_score = self.complexity_analyzer.complexity
            duplication_pct = self.duplication_detector.analyze_file(str(file_path), content)
            
            # Calculate maintainability index (simplified version)
            maintainability = max(0, 171 - 5.2 * (complexity_score / max(loc, 1)) - 0.23 * complexity_score - 16.2 * (loc / 1000))
            
            # Get test coverage (would integrate with coverage tools)
            test_coverage = await self._get_file_coverage(file_path)
            
            # Detect quality issues
            issues = await self._detect_issues(file_path, content, complexity_score, duplication_pct)
            
            # Create file report
            report = FileQualityReport(
                file_path=str(file_path),
                lines_of_code=loc,
                complexity_score=complexity_score,
                maintainability_index=maintainability,
                duplication_percentage=duplication_pct,
                test_coverage=test_coverage,
                issues=issues
            )
            
            # Calculate technical debt
            debt_minutes = self.debt_calculator.calculate_debt(report)
            for issue in report.issues:
                if not issue.debt_minutes:
                    issue.debt_minutes = debt_minutes // len(report.issues) if report.issues else 0
            
            return report
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return None
    
    async def _get_file_coverage(self, file_path: Path) -> float:
        """Get test coverage for a file (mock implementation)"""
        # This would integrate with actual coverage tools like coverage.py
        # For now, return a mock value based on file characteristics
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple heuristic: files with test imports likely have better coverage
            if 'import pytest' in content or 'import unittest' in content:
                return 85.0
            elif 'def test_' in content:
                return 90.0
            else:
                return 45.0  # Default assumption
        except:
            return 0.0
    
    async def _detect_issues(self, file_path: Path, content: str, 
                           complexity: float, duplication: float) -> List[QualityIssue]:
        """Detect quality issues in file"""
        issues = []
        lines = content.split('\n')
        
        # High complexity issues
        if complexity > self.thresholds["complexity"]["critical"]:
            issues.append(QualityIssue(
                file_path=str(file_path),
                line_number=1,
                metric=QualityMetric.COMPLEXITY,
                severity=Severity.CRITICAL,
                message=f"Very high complexity: {complexity}",
                suggestion="Consider breaking down into smaller functions",
                complexity_score=complexity,
                debt_minutes=30,
                rule_id="high_complexity"
            ))
        elif complexity > self.thresholds["complexity"]["warning"]:
            issues.append(QualityIssue(
                file_path=str(file_path),
                line_number=1,
                metric=QualityMetric.COMPLEXITY,
                severity=Severity.MEDIUM,
                message=f"High complexity: {complexity}",
                suggestion="Consider refactoring for better maintainability",
                complexity_score=complexity,
                debt_minutes=15,
                rule_id="medium_complexity"
            ))
        
        # Duplication issues
        if duplication > self.thresholds["duplication"]["critical"]:
            issues.append(QualityIssue(
                file_path=str(file_path),
                line_number=1,
                metric=QualityMetric.DUPLICATION,
                severity=Severity.HIGH,
                message=f"High code duplication: {duplication:.1f}%",
                suggestion="Extract common code into shared functions",
                debt_minutes=20,
                rule_id="high_duplication"
            ))
        
        # Long function detection
        current_function_start = None
        current_function_name = None
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Function start
            if stripped.startswith('def '):
                if current_function_start and i - current_function_start > 50:
                    issues.append(QualityIssue(
                        file_path=str(file_path),
                        line_number=current_function_start,
                        metric=QualityMetric.MAINTAINABILITY,
                        severity=Severity.MEDIUM,
                        message=f"Long function '{current_function_name}': {i - current_function_start} lines",
                        suggestion="Break down into smaller, focused functions",
                        debt_minutes=25,
                        rule_id="long_function"
                    ))
                
                current_function_start = i
                current_function_name = stripped.split('(')[0].replace('def ', '')
            
            # Magic numbers
            if re.search(r'\b\d{2,}\b', stripped) and not stripped.startswith('#'):
                issues.append(QualityIssue(
                    file_path=str(file_path),
                    line_number=i,
                    metric=QualityMetric.READABILITY,
                    severity=Severity.LOW,
                    message="Magic number detected",
                    suggestion="Consider using named constants",
                    debt_minutes=5,
                    rule_id="magic_number"
                ))
            
            # TODO comments (technical debt markers)
            if 'TODO' in stripped or 'FIXME' in stripped:
                issues.append(QualityIssue(
                    file_path=str(file_path),
                    line_number=i,
                    metric=QualityMetric.TECHNICAL_DEBT,
                    severity=Severity.MEDIUM,
                    message="Technical debt marker found",
                    suggestion="Address the TODO/FIXME comment",
                    debt_minutes=30,
                    rule_id="tech_debt_marker"
                ))
        
        return issues
    
    def generate_report(self, project_report: ProjectQualityReport, 
                       output_format: str = "console") -> str:
        """Generate quality report in various formats"""
        if output_format == "console":
            return self._generate_console_report(project_report)
        elif output_format == "json":
            return self._generate_json_report(project_report)
        elif output_format == "html":
            return self._generate_html_report(project_report)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _generate_console_report(self, report: ProjectQualityReport) -> str:
        """Generate console-friendly report"""
        output = []
        output.append("=" * 60)
        output.append(f"CODE QUALITY REPORT - {report.project_name}")
        output.append("=" * 60)
        output.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        output.append("")
        
        # Overview
        output.append("OVERVIEW:")
        output.append(f"  Total files analyzed: {report.total_files}")
        output.append(f"  Total lines of code: {report.total_lines_of_code:,}")
        output.append(f"  Average complexity: {report.average_complexity:.1f}")
        output.append(f"  Average maintainability: {report.average_maintainability:.1f}")
        output.append(f"  Overall test coverage: {report.overall_coverage:.1f}%")
        output.append(f"  Technical debt: {report.technical_debt_hours:.1f} hours")
        output.append("")
        
        # Quality distribution
        output.append("QUALITY GRADE DISTRIBUTION:")
        distribution = report.quality_distribution
        for grade, count in distribution.items():
            percentage = (count / report.total_files * 100) if report.total_files > 0 else 0
            output.append(f"  Grade {grade}: {count} files ({percentage:.1f}%)")
        output.append("")
        
        # Top issues
        all_issues = []
        for file_report in report.file_reports.values():
            all_issues.extend(file_report.issues)
        
        critical_issues = [i for i in all_issues if i.severity == Severity.CRITICAL]
        if critical_issues:
            output.append("CRITICAL ISSUES:")
            for issue in critical_issues[:10]:  # Show top 10
                output.append(f"  🔴 {Path(issue.file_path).name}:{issue.line_number}")
                output.append(f"      {issue.message}")
                if issue.suggestion:
                    output.append(f"      💡 {issue.suggestion}")
            output.append("")
        
        # Worst files
        worst_files = sorted(
            report.file_reports.values(),
            key=lambda x: (x.critical_issues_count, -x.maintainability_index),
            reverse=True
        )[:5]
        
        if worst_files:
            output.append("FILES NEEDING ATTENTION:")
            for file_report in worst_files:
                output.append(f"  📁 {Path(file_report.file_path).name}")
                output.append(f"      Grade: {file_report.quality_grade}, "
                             f"Complexity: {file_report.complexity_score:.1f}, "
                             f"Issues: {len(file_report.issues)}")
        
        return "\n".join(output)
    
    def _generate_json_report(self, report: ProjectQualityReport) -> str:
        """Generate JSON report"""
        data = {
            "project_name": report.project_name,
            "generated_at": report.generated_at.isoformat(),
            "summary": {
                "total_files": report.total_files,
                "total_lines_of_code": report.total_lines_of_code,
                "average_complexity": report.average_complexity,
                "average_maintainability": report.average_maintainability,
                "overall_coverage": report.overall_coverage,
                "technical_debt_hours": report.technical_debt_hours,
                "quality_distribution": report.quality_distribution,
                "total_issues": report.total_issues
            },
            "files": {}
        }
        
        for file_path, file_report in report.file_reports.items():
            data["files"][file_path] = {
                "lines_of_code": file_report.lines_of_code,
                "complexity_score": file_report.complexity_score,
                "maintainability_index": file_report.maintainability_index,
                "duplication_percentage": file_report.duplication_percentage,
                "test_coverage": file_report.test_coverage,
                "quality_grade": file_report.quality_grade,
                "technical_debt_minutes": file_report.technical_debt_minutes,
                "issues": [
                    {
                        "line_number": issue.line_number,
                        "metric": issue.metric.value,
                        "severity": issue.severity.value,
                        "message": issue.message,
                        "suggestion": issue.suggestion,
                        "debt_minutes": issue.debt_minutes,
                        "rule_id": issue.rule_id
                    }
                    for issue in file_report.issues
                ]
            }
        
        return json.dumps(data, indent=2)
    
    def _generate_html_report(self, report: ProjectQualityReport) -> str:
        """Generate HTML report"""
        # This would generate a comprehensive HTML report
        # For brevity, returning a simple template
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Code Quality Report - {report.project_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
                .grade-a {{ color: green; }}
                .grade-f {{ color: red; }}
                .issue-critical {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Code Quality Report - {report.project_name}</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p>Total files: {report.total_files}</p>
                <p>Average complexity: {report.average_complexity:.1f}</p>
                <p>Technical debt: {report.technical_debt_hours:.1f} hours</p>
            </div>
        </body>
        </html>
        """

# Example usage and testing
async def main():
    """Demonstrate code quality monitoring system"""
    logger.info("Starting Novel Engine Code Quality Monitoring Demo")
    
    # Initialize quality monitor
    monitor = QualityMonitor()
    
    # Analyze project
    project_report = await monitor.analyze_project()
    
    # Generate and display report
    console_report = monitor.generate_report(project_report, "console")
    print(console_report)
    
    # Save JSON report
    json_report = monitor.generate_report(project_report, "json")
    with open("quality_report.json", "w") as f:
        f.write(json_report)
    
    logger.info("Code quality monitoring demonstration complete")

if __name__ == "__main__":
    asyncio.run(main())