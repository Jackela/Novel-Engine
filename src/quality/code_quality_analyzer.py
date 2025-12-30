"""
Code Quality Analyzer and Technical Debt Assessment
==================================================

Advanced code quality analysis system for Novel Engine that identifies
technical debt, maintainability issues, and provides actionable improvement recommendations.

Wave 6.1 - Code Quality Analysis & Technical Debt Assessment
"""

import ast
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import radon.complexity as radon_cc
import radon.metrics as radon_metrics

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Issue severity levels for prioritization."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(Enum):
    """Categories of code quality issues."""

    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    ERROR_HANDLING = "error_handling"
    DESIGN_PATTERNS = "design_patterns"
    PERFORMANCE = "performance"
    SECURITY = "security"
    TESTING = "testing"


@dataclass
class QualityIssue:
    """Represents a code quality issue with context and recommendations."""

    file_path: str
    line_number: int
    issue_type: str
    category: IssueCategory
    severity: SeverityLevel
    description: str
    recommendation: str
    code_snippet: Optional[str] = None
    impact_score: float = 0.0
    estimated_fix_time: int = 0  # in minutes

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "issue_type": self.issue_type,
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "recommendation": self.recommendation,
            "code_snippet": self.code_snippet,
            "impact_score": self.impact_score,
            "estimated_fix_time": self.estimated_fix_time,
        }


@dataclass
class FileQualityMetrics:
    """Quality metrics for a single file."""

    file_path: str
    lines_of_code: int
    cyclomatic_complexity: float
    maintainability_index: float
    function_count: int
    class_count: int
    comment_ratio: float
    docstring_coverage: float
    type_hint_coverage: float
    issues: List[QualityIssue] = field(default_factory=list)

    def calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        # Base score starts at 100
        score = 100.0

        # Deduct for complexity issues
        if self.cyclomatic_complexity > 10:
            score -= min(30, (self.cyclomatic_complexity - 10) * 2)

        # Deduct for low maintainability
        if self.maintainability_index < 60:
            score -= (60 - self.maintainability_index) * 0.5

        # Deduct for poor documentation
        if self.docstring_coverage < 0.8:
            score -= (0.8 - self.docstring_coverage) * 20

        # Deduct for missing type hints
        if self.type_hint_coverage < 0.7:
            score -= (0.7 - self.type_hint_coverage) * 15

        # Deduct for critical and high severity issues
        for issue in self.issues:
            if issue.severity == SeverityLevel.CRITICAL:
                score -= 10
            elif issue.severity == SeverityLevel.HIGH:
                score -= 5
            elif issue.severity == SeverityLevel.MEDIUM:
                score -= 2

        return max(0.0, score)


class CodeQualityAnalyzer:
    """
    Comprehensive code quality analyzer for Python codebases.

    Features:
    - Complexity analysis using cyclomatic complexity
    - Maintainability index calculation
    - Documentation coverage assessment
    - Type hint coverage analysis
    - Design pattern violation detection
    - Error handling pattern analysis
    - Technical debt quantification
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.quality_issues: List[QualityIssue] = []
        self.file_metrics: Dict[str, FileQualityMetrics] = {}

        # Analysis patterns and rules
        self.complexity_threshold = 10
        self.function_length_threshold = 50
        self.class_length_threshold = 200
        self.maintainability_threshold = 60.0

        logger.info(f"CodeQualityAnalyzer initialized for {project_root}")

    def analyze_project(
        self, exclude_patterns: List[str] = None, max_files: int = 50
    ) -> Dict[str, Any]:
        """Analyze project for code quality issues with optimizations."""
        if exclude_patterns is None:
            exclude_patterns = ["test_*", "*_test.py", "tests/*", "__pycache__", ".git"]

        logger.info("Starting optimized code quality analysis")

        python_files = self._find_python_files(exclude_patterns)
        logger.info(f"Found {len(python_files)} Python files")

        # Limit analysis to prevent timeouts
        if len(python_files) > max_files:
            logger.info(f"Limiting analysis to {max_files} files for performance")
            # Prioritize key files by size and name patterns
            priority_files = []
            regular_files = []

            for file_path in python_files:
                file_name = file_path.name.lower()
                if any(
                    keyword in file_name
                    for keyword in [
                        "agent",
                        "director",
                        "engine",
                        "service",
                        "manager",
                        "core",
                    ]
                ):
                    priority_files.append(file_path)
                else:
                    regular_files.append(file_path)

            # Analyze all priority files + subset of regular files
            selected_files = (
                priority_files + regular_files[: max_files - len(priority_files)]
            )
            python_files = selected_files
            logger.info(
                f"Selected {len(python_files)} files for analysis ({len(priority_files)} priority)"
            )

        # Analyze each file with timeout protection
        analyzed_count = 0
        for file_path in python_files:
            try:
                self._analyze_file(file_path)
                analyzed_count += 1

                # Progress reporting every 10 files
                if analyzed_count % 10 == 0:
                    logger.info(
                        f"Analyzed {analyzed_count}/{len(python_files)} files..."
                    )

            except Exception as e:
                logger.error(f"Failed to analyze {file_path}: {e}")
                continue

        # Generate overall report
        report = self._generate_quality_report()

        logger.info(
            f"Analysis complete: {analyzed_count} files analyzed, {len(self.quality_issues)} issues found"
        )
        return report

    def _find_python_files(self, exclude_patterns: List[str]) -> List[Path]:
        """Find all Python files in project, excluding test files and patterns."""
        python_files = []

        for py_file in self.project_root.rglob("*.py"):
            # Check exclude patterns
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in str(py_file) or py_file.match(pattern):
                    should_exclude = True
                    break

            if not should_exclude:
                python_files.append(py_file)

        return sorted(python_files)

    def _analyze_file(self, file_path: Path) -> FileQualityMetrics:
        """Analyze a single Python file for quality issues."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            tree = ast.parse(content)

            # Calculate basic metrics
            lines = content.split("\n")
            loc = len(
                [
                    line
                    for line in lines
                    if line.strip() and not line.strip().startswith("#")
                ]
            )

            # Calculate complexity metrics
            complexity_results = radon_cc.cc_visit(content)
            avg_complexity = sum(item.complexity for item in complexity_results) / max(
                1, len(complexity_results)
            )

            # Calculate maintainability index
            try:
                mi_result = radon_metrics.mi_visit(content, True)
                maintainability_index = mi_result.mi
            except Exception:
                maintainability_index = 50.0  # Default if calculation fails

            # Count functions and classes
            function_count = len(
                [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            )
            class_count = len(
                [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            )

            # Calculate documentation metrics
            comment_ratio = self._calculate_comment_ratio(lines)
            docstring_coverage = self._calculate_docstring_coverage(tree)
            type_hint_coverage = self._calculate_type_hint_coverage(tree)

            # Create file metrics
            metrics = FileQualityMetrics(
                file_path=str(file_path.relative_to(self.project_root)),
                lines_of_code=loc,
                cyclomatic_complexity=avg_complexity,
                maintainability_index=maintainability_index,
                function_count=function_count,
                class_count=class_count,
                comment_ratio=comment_ratio,
                docstring_coverage=docstring_coverage,
                type_hint_coverage=type_hint_coverage,
            )

            # Analyze specific issues
            self._analyze_complexity_issues(file_path, tree, content, metrics)
            self._analyze_design_issues(file_path, tree, content, metrics)
            self._analyze_error_handling(file_path, tree, content, metrics)
            self._analyze_documentation_issues(file_path, tree, content, metrics)

            self.file_metrics[str(file_path)] = metrics
            return metrics

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            # Return minimal metrics on error
            return FileQualityMetrics(
                file_path=str(file_path.relative_to(self.project_root)),
                lines_of_code=0,
                cyclomatic_complexity=0,
                maintainability_index=0,
                function_count=0,
                class_count=0,
                comment_ratio=0,
                docstring_coverage=0,
                type_hint_coverage=0,
            )

    def _calculate_comment_ratio(self, lines: List[str]) -> float:
        """Calculate ratio of comment lines to total lines."""
        comment_lines = len([line for line in lines if line.strip().startswith("#")])
        total_lines = len([line for line in lines if line.strip()])
        return comment_lines / max(1, total_lines)

    def _calculate_docstring_coverage(self, tree: ast.AST) -> float:
        """Calculate percentage of functions/classes with docstrings."""
        total_items = 0
        documented_items = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                total_items += 1
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    documented_items += 1

        return documented_items / max(1, total_items)

    def _calculate_type_hint_coverage(self, tree: ast.AST) -> float:
        """Calculate percentage of functions with type hints."""
        total_functions = 0
        typed_functions = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_functions += 1
                # Check for return type annotation or argument type annotations
                if (
                    node.returns
                    or any(arg.annotation for arg in node.args.args)
                    or any(arg.annotation for arg in node.args.kwonlyargs)
                ):
                    typed_functions += 1

        return typed_functions / max(1, total_functions)

    def _analyze_complexity_issues(
        self, file_path: Path, tree: ast.AST, content: str, metrics: FileQualityMetrics
    ):
        """Analyze complexity-related issues."""
        content.split("\n")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check function length
                func_lines = (
                    node.end_lineno - node.lineno + 1
                    if hasattr(node, "end_lineno")
                    else 0
                )
                if func_lines > self.function_length_threshold:
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="long_function",
                        category=IssueCategory.COMPLEXITY,
                        severity=(
                            SeverityLevel.HIGH
                            if func_lines > 100
                            else SeverityLevel.MEDIUM
                        ),
                        description=f"Function '{node.name}' is too long ({func_lines} lines)",
                        recommendation=f"Break down function '{node.name}' into smaller, more focused functions",
                        impact_score=min(10.0, func_lines / 10),
                        estimated_fix_time=func_lines
                        * 2,  # 2 minutes per line to refactor
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

                # Check cyclomatic complexity for individual functions
                func_complexity = self._calculate_function_complexity(node)
                if func_complexity > self.complexity_threshold:
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="high_complexity",
                        category=IssueCategory.COMPLEXITY,
                        severity=(
                            SeverityLevel.HIGH
                            if func_complexity > 15
                            else SeverityLevel.MEDIUM
                        ),
                        description=f"Function '{node.name}' has high cyclomatic complexity ({func_complexity})",
                        recommendation=f"Reduce complexity in '{node.name}' by extracting methods or simplifying logic",
                        impact_score=func_complexity,
                        estimated_fix_time=func_complexity
                        * 15,  # 15 minutes per complexity point
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

            elif isinstance(node, ast.ClassDef):
                # Check class length
                class_lines = (
                    node.end_lineno - node.lineno + 1
                    if hasattr(node, "end_lineno")
                    else 0
                )
                if class_lines > self.class_length_threshold:
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="large_class",
                        category=IssueCategory.DESIGN_PATTERNS,
                        severity=(
                            SeverityLevel.HIGH
                            if class_lines > 500
                            else SeverityLevel.MEDIUM
                        ),
                        description=f"Class '{node.name}' is too large ({class_lines} lines)",
                        recommendation=f"Break down class '{node.name}' into smaller, more cohesive classes",
                        impact_score=min(10.0, class_lines / 50),
                        estimated_fix_time=class_lines
                        * 3,  # 3 minutes per line to refactor
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

    def _calculate_function_complexity(self, func_node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity for a single function."""
        complexity = 1  # Base complexity

        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def _analyze_design_issues(
        self, file_path: Path, tree: ast.AST, content: str, metrics: FileQualityMetrics
    ):
        """Analyze design pattern and architecture issues."""
        lines = content.split("\n")

        # Check for god classes (classes with too many methods)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = len(
                    [n for n in node.body if isinstance(n, ast.FunctionDef)]
                )
                if method_count > 20:
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="god_class",
                        category=IssueCategory.DESIGN_PATTERNS,
                        severity=(
                            SeverityLevel.HIGH
                            if method_count > 30
                            else SeverityLevel.MEDIUM
                        ),
                        description=f"Class '{node.name}' has too many methods ({method_count})",
                        recommendation=f"Apply Single Responsibility Principle to '{node.name}' - extract related methods into separate classes",
                        impact_score=method_count / 5,
                        estimated_fix_time=method_count
                        * 30,  # 30 minutes per method to reorganize
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

        # Check for hard-coded values (magic numbers/strings)
        magic_number_pattern = re.compile(r"\b(?!0|1|2|10|100|1000)\d{2,}\b")
        for i, line in enumerate(lines, 1):
            if magic_number_pattern.search(line) and not line.strip().startswith("#"):
                issue = QualityIssue(
                    file_path=str(file_path.relative_to(self.project_root)),
                    line_number=i,
                    issue_type="magic_number",
                    category=IssueCategory.MAINTAINABILITY,
                    severity=SeverityLevel.MEDIUM,
                    description="Hard-coded magic number found",
                    recommendation="Replace magic number with named constant",
                    code_snippet=line.strip(),
                    impact_score=2.0,
                    estimated_fix_time=10,  # 10 minutes to extract constant
                )
                metrics.issues.append(issue)
                self.quality_issues.append(issue)

    def _analyze_error_handling(
        self, file_path: Path, tree: ast.AST, content: str, metrics: FileQualityMetrics
    ):
        """Analyze error handling patterns."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Check for bare except clauses
                if node.type is None:
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="bare_except",
                        category=IssueCategory.ERROR_HANDLING,
                        severity=SeverityLevel.HIGH,
                        description="Bare except clause catches all exceptions",
                        recommendation="Use specific exception types instead of bare except",
                        impact_score=5.0,
                        estimated_fix_time=20,  # 20 minutes to identify proper exceptions
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

                # Check for overly broad exception handling
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="broad_exception",
                        category=IssueCategory.ERROR_HANDLING,
                        severity=SeverityLevel.MEDIUM,
                        description="Overly broad Exception catch",
                        recommendation="Use more specific exception types when possible",
                        impact_score=3.0,
                        estimated_fix_time=15,  # 15 minutes to refine exception handling
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

    def _analyze_documentation_issues(
        self, file_path: Path, tree: ast.AST, content: str, metrics: FileQualityMetrics
    ):
        """Analyze documentation and type hint issues."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for missing docstrings
                if not (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    # Skip very simple functions (less than 3 lines)
                    func_lines = (
                        node.end_lineno - node.lineno + 1
                        if hasattr(node, "end_lineno")
                        else 0
                    )
                    if func_lines > 3 and not node.name.startswith(
                        "_"
                    ):  # Skip private methods for now
                        issue = QualityIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            line_number=node.lineno,
                            issue_type="missing_docstring",
                            category=IssueCategory.DOCUMENTATION,
                            severity=SeverityLevel.MEDIUM,
                            description=f"Function '{node.name}' missing docstring",
                            recommendation=f"Add comprehensive docstring to '{node.name}' explaining purpose, parameters, and return value",
                            impact_score=2.0,
                            estimated_fix_time=15,  # 15 minutes to write good docstring
                        )
                        metrics.issues.append(issue)
                        self.quality_issues.append(issue)

                # Check for missing type hints
                if (
                    not node.returns and len(node.args.args) > 1
                ):  # Skip simple functions
                    issue = QualityIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        line_number=node.lineno,
                        issue_type="missing_type_hints",
                        category=IssueCategory.DOCUMENTATION,
                        severity=SeverityLevel.LOW,
                        description=f"Function '{node.name}' missing type hints",
                        recommendation=f"Add type hints to '{node.name}' for better code clarity and IDE support",
                        impact_score=1.0,
                        estimated_fix_time=10,  # 10 minutes to add type hints
                    )
                    metrics.issues.append(issue)
                    self.quality_issues.append(issue)

    def _generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        # Calculate overall statistics
        total_files = len(self.file_metrics)
        total_issues = len(self.quality_issues)

        # Group issues by severity and category
        issues_by_severity = {level.value: [] for level in SeverityLevel}
        issues_by_category = {cat.value: [] for cat in IssueCategory}

        for issue in self.quality_issues:
            issues_by_severity[issue.severity.value].append(issue)
            issues_by_category[issue.category.value].append(issue)

        # Calculate file quality scores
        quality_scores = []
        for metrics in self.file_metrics.values():
            quality_scores.append(metrics.calculate_quality_score())

        overall_quality_score = sum(quality_scores) / max(1, len(quality_scores))

        # Calculate technical debt metrics
        total_fix_time = sum(issue.estimated_fix_time for issue in self.quality_issues)
        technical_debt_hours = total_fix_time / 60

        # Find most problematic files
        worst_files = sorted(
            self.file_metrics.values(),
            key=lambda m: len(
                [
                    i
                    for i in m.issues
                    if i.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
                ]
            ),
            reverse=True,
        )[:10]

        return {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "summary": {
                "total_files": total_files,
                "total_issues": total_issues,
                "overall_quality_score": overall_quality_score,
                "technical_debt_hours": technical_debt_hours,
                "maintainability_grade": self._calculate_maintainability_grade(
                    overall_quality_score
                ),
            },
            "issues_by_severity": {
                severity: len(issues) for severity, issues in issues_by_severity.items()
            },
            "issues_by_category": {
                category: len(issues) for category, issues in issues_by_category.items()
            },
            "most_problematic_files": [
                {
                    "file": f.file_path,
                    "quality_score": f.calculate_quality_score(),
                    "critical_issues": len(
                        [i for i in f.issues if i.severity == SeverityLevel.CRITICAL]
                    ),
                    "high_issues": len(
                        [i for i in f.issues if i.severity == SeverityLevel.HIGH]
                    ),
                    "total_issues": len(f.issues),
                }
                for f in worst_files
            ],
            "detailed_issues": [issue.to_dict() for issue in self.quality_issues],
            "recommendations": self._generate_recommendations(),
        }

    def _calculate_maintainability_grade(self, quality_score: float) -> str:
        """Calculate maintainability letter grade."""
        if quality_score >= 90:
            return "A+"
        elif quality_score >= 80:
            return "A"
        elif quality_score >= 70:
            return "B"
        elif quality_score >= 60:
            return "C"
        elif quality_score >= 50:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate prioritized recommendations for improvement."""
        recommendations = []

        # Critical issues first
        critical_issues = [
            i for i in self.quality_issues if i.severity == SeverityLevel.CRITICAL
        ]
        if critical_issues:
            recommendations.append(
                {
                    "priority": 1,
                    "title": "Address Critical Technical Debt",
                    "description": f"Fix {len(critical_issues)} critical issues that severely impact maintainability",
                    "estimated_hours": sum(
                        i.estimated_fix_time for i in critical_issues
                    )
                    / 60,
                    "files_affected": len(set(i.file_path for i in critical_issues)),
                }
            )

        # High priority issues
        high_issues = [
            i for i in self.quality_issues if i.severity == SeverityLevel.HIGH
        ]
        if high_issues:
            recommendations.append(
                {
                    "priority": 2,
                    "title": "Resolve High-Priority Issues",
                    "description": f"Address {len(high_issues)} high-priority maintainability issues",
                    "estimated_hours": sum(i.estimated_fix_time for i in high_issues)
                    / 60,
                    "files_affected": len(set(i.file_path for i in high_issues)),
                }
            )

        # Documentation improvements
        doc_issues = [
            i for i in self.quality_issues if i.category == IssueCategory.DOCUMENTATION
        ]
        if doc_issues:
            recommendations.append(
                {
                    "priority": 3,
                    "title": "Improve Documentation Coverage",
                    "description": "Add docstrings and type hints to improve code clarity",
                    "estimated_hours": sum(i.estimated_fix_time for i in doc_issues)
                    / 60,
                    "files_affected": len(set(i.file_path for i in doc_issues)),
                }
            )

        return recommendations

    def export_report(self, output_path: str):
        """Export quality report to file."""
        report = self._generate_quality_report()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(
                f"# Code Quality Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            )
            f.write("## Summary\n")
            f.write(f"- **Files Analyzed**: {report['summary']['total_files']}\n")
            f.write(f"- **Total Issues**: {report['summary']['total_issues']}\n")
            f.write(
                f"- **Quality Score**: {report['summary']['overall_quality_score']:.1f}/100\n"
            )
            f.write(
                f"- **Maintainability Grade**: {report['summary']['maintainability_grade']}\n"
            )
            f.write(
                f"- **Technical Debt**: {report['summary']['technical_debt_hours']:.1f} hours\n\n"
            )

            f.write("## Issues by Severity\n")
            for severity, count in report["issues_by_severity"].items():
                f.write(f"- **{severity.title()}**: {count}\n")

            f.write("\n## Most Problematic Files\n")
            for file_info in report["most_problematic_files"][:5]:
                f.write(
                    f"- `{file_info['file']}` (Score: {file_info['quality_score']:.1f}, Issues: {file_info['total_issues']})\n"
                )

            f.write("\n## Priority Recommendations\n")
            for rec in report["recommendations"]:
                f.write(
                    f"{rec['priority']}. **{rec['title']}** ({rec['estimated_hours']:.1f}h, {rec['files_affected']} files)\n"
                )
                f.write(f"   {rec['description']}\n\n")

        logger.info(f"Quality report exported to {output_path}")


# Utility functions for easy usage
def analyze_codebase(
    project_root: str, output_file: str = "code_quality_report.md"
) -> Dict[str, Any]:
    """Quick analysis of entire codebase."""
    analyzer = CodeQualityAnalyzer(project_root)
    report = analyzer.analyze_project()

    if output_file:
        analyzer.export_report(output_file)

    return report


def get_file_quality_score(file_path: str) -> float:
    """Get quality score for a single file."""
    analyzer = CodeQualityAnalyzer(os.path.dirname(file_path))
    metrics = analyzer._analyze_file(Path(file_path))
    return metrics.calculate_quality_score()
