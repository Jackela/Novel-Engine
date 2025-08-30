#!/usr/bin/env python3
"""
Quality Gates Validation System

Automated quality gates for Novel Engine maintainability improvements.
Validates code quality, structure, and adherence to standards.
"""

import ast
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    """Quality gate levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityIssue:
    """Represents a quality issue found during validation."""

    file_path: str
    line_number: int
    issue_type: str
    message: str
    level: QualityLevel
    suggestion: str = ""


@dataclass
class QualityMetrics:
    """Quality metrics for the codebase."""

    total_files: int = 0
    total_lines: int = 0
    avg_file_size: float = 0.0
    max_file_size: int = 0
    files_over_500_lines: int = 0
    files_over_1000_lines: int = 0
    functions_over_50_lines: int = 0
    classes_over_30_methods: int = 0
    unprofessional_comments: int = 0
    missing_docstrings: int = 0
    total_issues: int = 0


class QualityGateValidator:
    """Validates codebase against quality gates."""

    def __init__(self, project_root: str):
        """Initialize validator with project root."""
        self.project_root = Path(project_root)
        self.issues: List[QualityIssue] = []
        self.metrics = QualityMetrics()

        # Patterns to check for unprofessional content
        self.unprofessional_patterns = [
            "SACRED",
            "BLESSED",
            "++",
            "万机之神",
            "Tech-Priest",
            "OMNISSIAH",
            "Holy",
            "Divine",
            "Mechanicus",
        ]

    def validate_all(self) -> Tuple[QualityMetrics, List[QualityIssue]]:
        """Run all quality gate validations."""
        logger.info("Starting quality gate validation")

        # Find all Python files
        python_files = list(self.project_root.rglob("*.py"))
        python_files = [f for f in python_files if not self._should_skip_file(f)]

        self.metrics.total_files = len(python_files)

        for file_path in python_files:
            self._validate_file(file_path)

        self._calculate_metrics()
        self.metrics.total_issues = len(self.issues)

        logger.info(f"Quality validation complete: {len(self.issues)} issues found")
        return self.metrics, self.issues

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped."""
        skip_patterns = [
            "__pycache__",
            ".git",
            "node_modules",
            "venv",
            "env",
            "dist",
            "build",
            ".pytest_cache",
            "htmlcov",
        ]

        for pattern in skip_patterns:
            if pattern in str(file_path):
                return True

        return False

    def _validate_file(self, file_path: Path) -> None:
        """Validate a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            self.metrics.total_lines += len(lines)

            # Parse AST for structural analysis
            try:
                tree = ast.parse(content)
                self._validate_ast(file_path, tree, lines)
            except SyntaxError as e:
                self.issues.append(
                    QualityIssue(
                        file_path=str(file_path),
                        line_number=e.lineno or 0,
                        issue_type="syntax_error",
                        message=f"Syntax error: {e.msg}",
                        level=QualityLevel.CRITICAL,
                    )
                )

            # Validate file-level issues
            self._validate_file_size(file_path, lines)
            self._validate_unprofessional_content(file_path, lines)

        except Exception as e:
            logger.error(f"Error validating file {file_path}: {e}")

    def _validate_ast(self, file_path: Path, tree: ast.AST, lines: List[str]) -> None:
        """Validate AST structure."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self._validate_function(file_path, node, lines)
            elif isinstance(node, ast.ClassDef):
                self._validate_class(file_path, node, lines)

    def _validate_file_size(self, file_path: Path, lines: List[str]) -> None:
        """Validate file size constraints."""
        line_count = len(lines)

        if line_count > 1000:
            self.metrics.files_over_1000_lines += 1
            self.issues.append(
                QualityIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="file_too_large",
                    message=f"File has {line_count} lines (exceeds 1000 line limit)",
                    level=QualityLevel.HIGH,
                    suggestion="Break this file into smaller, focused modules",
                )
            )
        elif line_count > 500:
            self.metrics.files_over_500_lines += 1
            self.issues.append(
                QualityIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="file_large",
                    message=f"File has {line_count} lines (approaching 1000 line limit)",
                    level=QualityLevel.MEDIUM,
                    suggestion="Consider breaking this file into smaller modules",
                )
            )

    def _validate_function(
        self, file_path: Path, node: ast.FunctionDef, lines: List[str]
    ) -> None:
        """Validate function structure."""
        # Calculate function length
        start_line = node.lineno - 1
        end_line = node.end_lineno - 1 if node.end_lineno else start_line
        func_length = end_line - start_line + 1

        if func_length > 50:
            self.metrics.functions_over_50_lines += 1
            self.issues.append(
                QualityIssue(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    issue_type="function_too_long",
                    message=f"Function '{node.name}' has {func_length} lines (exceeds 50 line limit)",
                    level=QualityLevel.MEDIUM,
                    suggestion="Break this function into smaller, focused functions",
                )
            )

        # Check for docstring
        if not ast.get_docstring(node):
            self.metrics.missing_docstrings += 1
            self.issues.append(
                QualityIssue(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    issue_type="missing_docstring",
                    message=f"Function '{node.name}' missing docstring",
                    level=QualityLevel.LOW,
                    suggestion="Add docstring explaining function purpose, parameters, and return value",
                )
            )

    def _validate_class(
        self, file_path: Path, node: ast.ClassDef, lines: List[str]
    ) -> None:
        """Validate class structure."""
        # Count methods
        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
        method_count = len(methods)

        if method_count > 30:
            self.metrics.classes_over_30_methods += 1
            self.issues.append(
                QualityIssue(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    issue_type="class_too_many_methods",
                    message=f"Class '{node.name}' has {method_count} methods (exceeds 30 method limit)",
                    level=QualityLevel.HIGH,
                    suggestion="Break this class into smaller, focused classes using composition",
                )
            )

        # Check for docstring
        if not ast.get_docstring(node):
            self.metrics.missing_docstrings += 1
            self.issues.append(
                QualityIssue(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    issue_type="missing_docstring",
                    message=f"Class '{node.name}' missing docstring",
                    level=QualityLevel.LOW,
                    suggestion="Add docstring explaining class purpose and responsibilities",
                )
            )

    def _validate_unprofessional_content(
        self, file_path: Path, lines: List[str]
    ) -> None:
        """Check for unprofessional content."""
        for line_num, line in enumerate(lines, 1):
            for pattern in self.unprofessional_patterns:
                if pattern in line:
                    self.metrics.unprofessional_comments += 1
                    self.issues.append(
                        QualityIssue(
                            file_path=str(file_path),
                            line_number=line_num,
                            issue_type="unprofessional_content",
                            message=f"Unprofessional content found: '{pattern}'",
                            level=QualityLevel.MEDIUM,
                            suggestion="Replace with professional, technical terminology",
                        )
                    )

    def _calculate_metrics(self) -> None:
        """Calculate aggregate metrics."""
        if self.metrics.total_files > 0:
            self.metrics.avg_file_size = (
                self.metrics.total_lines / self.metrics.total_files
            )

        # Find maximum file size
        for file_path in self.project_root.rglob("*.py"):
            if not self._should_skip_file(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        line_count = len(f.readlines())
                        self.metrics.max_file_size = max(
                            self.metrics.max_file_size, line_count
                        )
                except Exception:
                    pass

    def generate_report(self) -> str:
        """Generate quality report."""
        report = []
        report.append("# Novel Engine Quality Gate Report")
        report.append("=" * 50)
        report.append("")

        # Metrics summary
        report.append("## Quality Metrics")
        report.append(f"- Total Python files: {self.metrics.total_files}")
        report.append(f"- Total lines of code: {self.metrics.total_lines:,}")
        report.append(f"- Average file size: {self.metrics.avg_file_size:.1f} lines")
        report.append(f"- Largest file: {self.metrics.max_file_size} lines")
        report.append(f"- Files over 500 lines: {self.metrics.files_over_500_lines}")
        report.append(f"- Files over 1000 lines: {self.metrics.files_over_1000_lines}")
        report.append(
            f"- Functions over 50 lines: {self.metrics.functions_over_50_lines}"
        )
        report.append(
            f"- Classes over 30 methods: {self.metrics.classes_over_30_methods}"
        )
        report.append(
            f"- Unprofessional comments: {self.metrics.unprofessional_comments}"
        )
        report.append(f"- Missing docstrings: {self.metrics.missing_docstrings}")
        report.append("")

        # Issues summary
        critical_issues = [i for i in self.issues if i.level == QualityLevel.CRITICAL]
        high_issues = [i for i in self.issues if i.level == QualityLevel.HIGH]
        medium_issues = [i for i in self.issues if i.level == QualityLevel.MEDIUM]
        low_issues = [i for i in self.issues if i.level == QualityLevel.LOW]

        report.append("## Issues Summary")
        report.append(f"- Critical: {len(critical_issues)}")
        report.append(f"- High: {len(high_issues)}")
        report.append(f"- Medium: {len(medium_issues)}")
        report.append(f"- Low: {len(low_issues)}")
        report.append(f"- **Total: {len(self.issues)}**")
        report.append("")

        # Quality gate status
        if len(critical_issues) > 0:
            status = "🔴 FAILED"
        elif len(high_issues) > 10:
            status = "🟡 WARNING"
        elif len(medium_issues) > 20:
            status = "🟡 WARNING"
        else:
            status = "🟢 PASSED"

        report.append(f"## Quality Gate Status: {status}")
        report.append("")

        # Detailed issues
        if self.issues:
            report.append("## Detailed Issues")
            report.append("")

            for level in [
                QualityLevel.CRITICAL,
                QualityLevel.HIGH,
                QualityLevel.MEDIUM,
                QualityLevel.LOW,
            ]:
                level_issues = [i for i in self.issues if i.level == level]
                if level_issues:
                    report.append(
                        f"### {level.value.title()} Issues ({len(level_issues)})"
                    )
                    report.append("")

                    for issue in level_issues[:10]:  # Limit to first 10 per level
                        report.append(f"**{issue.file_path}:{issue.line_number}**")
                        report.append(f"- Type: {issue.issue_type}")
                        report.append(f"- Message: {issue.message}")
                        if issue.suggestion:
                            report.append(f"- Suggestion: {issue.suggestion}")
                        report.append("")

                    if len(level_issues) > 10:
                        report.append(
                            f"... and {len(level_issues) - 10} more {level.value} issues"
                        )
                        report.append("")

        return "\n".join(report)


def main():
    """Run quality gate validation."""
    logging.basicConfig(level=logging.INFO)

    project_root = Path(__file__).parent
    validator = QualityGateValidator(str(project_root))

    metrics, issues = validator.validate_all()
    report = validator.generate_report()

    # Save report
    report_path = project_root / "QUALITY_GATE_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Quality gate report saved to: {report_path}")
    print(f"Total issues found: {len(issues)}")

    # Exit with appropriate code
    critical_issues = [i for i in issues if i.level == QualityLevel.CRITICAL]
    if critical_issues:
        print(f"❌ Quality gates FAILED: {len(critical_issues)} critical issues")
        return 1
    else:
        print("✅ Quality gates PASSED")
        return 0


if __name__ == "__main__":
    exit(main())
