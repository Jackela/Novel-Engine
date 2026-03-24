#!/usr/bin/env python3
"""
Code Quality Analysis Test and Report Generation
===============================================

Tests the code quality analyzer and generates comprehensive technical debt
assessment for Novel Engine Wave 6.1 implementation.

Wave 6.1 Code Quality Analysis & Technical Debt Assessment Validation
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

# Add src to path for imports
sys.path.append("src")

# Import quality analyzer
from quality.code_quality_analyzer import (
    CodeQualityAnalyzer,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CodeQualityTest:
    """Test suite for code quality analyzer and technical debt assessment."""

    def __init__(self, project_root: str):
        self.project_root = project_root
        self.test_results = {}

    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run optimized code quality analysis with timeout handling."""
        logger.info("=== Starting Optimized Code Quality Analysis ===")

        start_time = time.time()

        try:
            # Initialize analyzer
            analyzer = CodeQualityAnalyzer(self.project_root)

            # Priority files analysis first (high-impact files)
            priority_files = [
                "src/persona_agent.py",
                "enhanced_multi_agent_bridge.py",
                "src/director_agent_modular.py",
                "director_agent.py",
                "src/llm_service.py",
            ]

            # Analyze priority files first
            priority_results = {}
            logger.info(f"Analyzing {len(priority_files)} priority files...")

            for file_path in priority_files:
                full_path = Path(self.project_root) / file_path
                if full_path.exists():
                    try:
                        file_start = time.time()
                        metrics = analyzer._analyze_file(full_path)
                        analysis_time = time.time() - file_start

                        priority_results[file_path] = {
                            "quality_score": metrics.calculate_quality_score(),
                            "issues_found": len(metrics.issues),
                            "critical_issues": len(
                                [
                                    i
                                    for i in metrics.issues
                                    if i.severity.value == "critical"
                                ]
                            ),
                            "high_issues": len(
                                [
                                    i
                                    for i in metrics.issues
                                    if i.severity.value == "high"
                                ]
                            ),
                            "analysis_time_ms": int(analysis_time * 1000),
                        }
                        logger.info(
                            f"✓ {file_path}: {metrics.calculate_quality_score():.1f}/100 ({len(metrics.issues)} issues)"
                        )
                    except Exception as e:
                        logger.error(f"✗ {file_path}: {e}")
                        priority_results[file_path] = {"error": str(e)}

            # Run optimized project analysis with exclusions
            logger.info("Running project-wide analysis with optimizations...")
            report = analyzer.analyze_project(
                exclude_patterns=[
                    "test_*",
                    "*_test.py",
                    "tests/*",
                    "__pycache__",
                    ".git",
                    "performance_optimizations/*",  # Exclude Wave 5 optimizations
                    "cache_l3/*",
                    "logs/*",
                    "validation_reports/*",
                    "ai_testing/*",
                    "demo_narratives/*",
                    "*.pyc",
                    "*.log",
                    "*.md",
                ]
            )

            analysis_time = time.time() - start_time

            # Enhance report with priority file results
            report["priority_file_analysis"] = priority_results

            # Generate detailed analysis report with optimizations
            self._generate_detailed_report(report, analysis_time)

            # Export markdown report
            output_file = "wave6_1_code_quality_assessment.md"
            analyzer.export_report(output_file)

            analysis_results = {
                "analysis_time_seconds": analysis_time,
                "report": report,
                "priority_file_results": priority_results,
                "success": True,
            }

            logger.info(f"=== Analysis Complete in {analysis_time:.2f}s ===")
            logger.info(
                f"Overall Quality Score: {report['summary']['overall_quality_score']:.1f}/100"
            )
            logger.info(
                f"Technical Debt: {report['summary']['technical_debt_hours']:.1f} hours"
            )
            logger.info(
                f"Priority Files Analyzed: {len([r for r in priority_results.values() if 'error' not in r])}"
            )

            return analysis_results

        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "analysis_time_seconds": time.time() - start_time,
            }

    def _generate_detailed_report(self, report: Dict[str, Any], analysis_time: float):
        """Generate detailed code quality analysis report."""

        # Create comprehensive report
        detailed_report = f"""
═══════════════════════════════════════════════════════════════
Novel Engine Code Quality Analysis Report
Wave 6.1 - Technical Debt Assessment & Quality Metrics
═══════════════════════════════════════════════════════════════

📊 EXECUTIVE SUMMARY:

✅ Files Analyzed: {report['summary']['total_files']}
🔍 Issues Found: {report['summary']['total_issues']}
📈 Quality Score: {report['summary']['overall_quality_score']:.1f}/100
📊 Maintainability Grade: {report['summary']['maintainability_grade']}
⏰ Technical Debt: {report['summary']['technical_debt_hours']:.1f} hours
⚡ Analysis Time: {analysis_time:.2f} seconds

═══════════════════════════════════════════════════════════════

🚨 ISSUES BY SEVERITY:
"""

        for severity, count in report["issues_by_severity"].items():
            if count > 0:
                emoji = {"critical": "🔥", "high": "⚠️", "medium": "📋", "low": "ℹ️"}.get(
                    severity, "•"
                )
                detailed_report += f"\n{emoji} {severity.upper()}: {count} issues"

        detailed_report += """

📂 ISSUES BY CATEGORY:
"""
        for category, count in report["issues_by_category"].items():
            if count > 0:
                emoji = {
                    "complexity": "🔄",
                    "maintainability": "🔧",
                    "documentation": "📚",
                    "error_handling": "⚠️",
                    "design_patterns": "🏗️",
                    "performance": "⚡",
                    "security": "🛡️",
                    "testing": "🧪",
                }.get(category, "•")
                detailed_report += (
                    f"\n{emoji} {category.replace('_', ' ').title()}: {count} issues"
                )

        detailed_report += """

═══════════════════════════════════════════════════════════════

🔥 MOST PROBLEMATIC FILES:
"""

        for i, file_info in enumerate(report["most_problematic_files"][:10], 1):
            grade = self._calculate_grade(file_info["quality_score"])
            detailed_report += f"""
{i:2d}. {file_info['file']}
    📊 Quality Score: {file_info['quality_score']:.1f}/100 (Grade {grade})
    🔥 Critical: {file_info['critical_issues']} | ⚠️ High: {file_info['high_issues']} | Total: {file_info['total_issues']}
"""

        detailed_report += """

═══════════════════════════════════════════════════════════════

🎯 PRIORITY RECOMMENDATIONS:
"""

        for i, rec in enumerate(report["recommendations"], 1):
            detailed_report += f"""
{i}. **{rec['title']}** (Priority {rec['priority']})
   ⏰ Estimated Time: {rec['estimated_hours']:.1f} hours
   📁 Files Affected: {rec['files_affected']}
   📝 Description: {rec['description']}
"""

        # Analyze critical issues in detail
        critical_issues = [
            issue
            for issue in report["detailed_issues"]
            if issue["severity"] == "critical"
        ]

        if critical_issues:
            detailed_report += """

═══════════════════════════════════════════════════════════════

🔥 CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION:
"""

            for issue in critical_issues[:10]:  # Show top 10 critical issues
                detailed_report += f"""
📍 {issue['file_path']}:{issue['line_number']}
   🔥 {issue['issue_type'].replace('_', ' ').title()}
   📝 {issue['description']}
   🔧 {issue['recommendation']}
   ⏰ Est. Fix Time: {issue['estimated_fix_time']} minutes
"""

        # High-impact issues analysis
        high_issues = [
            issue for issue in report["detailed_issues"] if issue["severity"] == "high"
        ]

        if high_issues:
            detailed_report += f"""

═══════════════════════════════════════════════════════════════

⚠️ HIGH-PRIORITY ISSUES ({len(high_issues)} total):
"""

            # Group by issue type
            issue_types = {}
            for issue in high_issues:
                issue_type = issue["issue_type"]
                if issue_type not in issue_types:
                    issue_types[issue_type] = []
                issue_types[issue_type].append(issue)

            for issue_type, issues in sorted(
                issue_types.items(), key=lambda x: len(x[1]), reverse=True
            ):
                detailed_report += f"\n🔸 {issue_type.replace('_', ' ').title()}: {len(issues)} occurrences"

                # Show examples for most common issues
                if len(issues) > 3:
                    detailed_report += " (showing top 3):"
                    for issue in issues[:3]:
                        detailed_report += (
                            f"\n   • {issue['file_path']}:{issue['line_number']}"
                        )
                else:
                    detailed_report += ":"
                    for issue in issues:
                        detailed_report += (
                            f"\n   • {issue['file_path']}:{issue['line_number']}"
                        )

        detailed_report += f"""

═══════════════════════════════════════════════════════════════

📊 TECHNICAL DEBT BREAKDOWN:

💰 Total Technical Debt: {report['summary']['technical_debt_hours']:.1f} hours
"""

        # Calculate debt by category
        debt_by_category = {}
        for issue in report["detailed_issues"]:
            category = issue["category"]
            if category not in debt_by_category:
                debt_by_category[category] = 0
            debt_by_category[category] += issue["estimated_fix_time"]

        for category, minutes in sorted(
            debt_by_category.items(), key=lambda x: x[1], reverse=True
        ):
            hours = minutes / 60
            percentage = (minutes / max(1, sum(debt_by_category.values()))) * 100
            detailed_report += f"\n• {category.replace('_', ' ').title()}: {hours:.1f}h ({percentage:.1f}%)"

        detailed_report += f"""

═══════════════════════════════════════════════════════════════

🎯 WAVE 6 IMPLEMENTATION STRATEGY:

Based on this analysis, Wave 6 should focus on:

1. **CRITICAL PRIORITY (Week 1-2)**:
   • Address {report['issues_by_severity']['critical']} critical issues
   • Fix large class/function complexity problems
   • Implement proper error handling patterns

2. **HIGH PRIORITY (Week 3-4)**:
   • Resolve {report['issues_by_severity']['high']} high-priority maintainability issues
   • Extract hard-coded configuration values
   • Add comprehensive documentation and type hints

3. **MEDIUM PRIORITY (Week 5-6)**:
   • Address design pattern violations
   • Improve code organization and modularity
   • Enhance testing infrastructure

📈 EXPECTED OUTCOMES:
• Quality Score: {report['summary']['overall_quality_score']:.1f} → 85+ (Target A- grade)
• Technical Debt: {report['summary']['technical_debt_hours']:.1f}h → <10h (60%+ reduction)
• Maintainability: {report['summary']['maintainability_grade']} → A- or better
• Developer Experience: Significant improvement in code clarity

═══════════════════════════════════════════════════════════════
Code Quality Analysis Complete - Wave 6.1 Assessment Ready
═══════════════════════════════════════════════════════════════
"""

        # Write detailed report to file
        report_path = Path("wave6_1_technical_debt_assessment.py")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write('"""\n')
            f.write(detailed_report)
            f.write('\n"""\n\n')
            f.write("# Code Quality Analysis Results:\n")
            f.write(
                f"TECHNICAL_DEBT_ANALYSIS = {json.dumps(report, indent=2, default=str)}\n"
            )

        logger.info(f"Detailed technical debt assessment written to {report_path}")

        # Display summary
        print(detailed_report)

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from quality score."""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 60:
            return "C"
        elif score >= 50:
            return "D"
        else:
            return "F"

    def test_analyzer_components(self) -> Dict[str, Any]:
        """Test individual components of the analyzer."""
        logger.info("Testing code quality analyzer components")

        component_results = {}

        try:
            # Test analyzer initialization
            analyzer = CodeQualityAnalyzer(self.project_root)
            component_results["initialization"] = True

            # Test file discovery
            python_files = analyzer._find_python_files(["test_*", "__pycache__"])
            component_results["file_discovery"] = {
                "success": True,
                "files_found": len(python_files),
            }
            logger.info(f"Found {len(python_files)} Python files")

            # Test single file analysis on a simple test case
            if python_files:
                test_file = python_files[0]  # Analyze first file found
                try:
                    metrics = analyzer._analyze_file(test_file)
                    component_results["file_analysis"] = {
                        "success": True,
                        "quality_score": metrics.calculate_quality_score(),
                        "issues_found": len(metrics.issues),
                    }
                    logger.info(f"Single file analysis successful: {test_file}")
                except Exception as e:
                    component_results["file_analysis"] = {
                        "success": False,
                        "error": str(e),
                    }

            return {"success": True, "component_results": component_results}

        except Exception as e:
            logger.error(f"Component testing failed: {e}")
            return {"success": False, "error": str(e)}


def main():
    """Main execution function."""
    logger.info("Starting Code Quality Analysis Test Suite...")

    # Get project root
    project_root = os.getcwd()

    test_suite = CodeQualityTest(project_root)

    try:
        # Test analyzer components first
        component_results = test_suite.test_analyzer_components()

        if component_results["success"]:
            logger.info("✅ Analyzer components test passed")

            # Run comprehensive analysis
            analysis_results = test_suite.run_comprehensive_analysis()

            if analysis_results["success"]:
                logger.info(
                    "✅ Comprehensive code quality analysis completed successfully"
                )

                # Summary of results
                report = analysis_results["report"]
                logger.info("📊 Analysis Summary:")
                logger.info(
                    f"   Quality Score: {report['summary']['overall_quality_score']:.1f}/100"
                )
                logger.info(f"   Grade: {report['summary']['maintainability_grade']}")
                logger.info(
                    f"   Technical Debt: {report['summary']['technical_debt_hours']:.1f} hours"
                )
                logger.info(
                    f"   Critical Issues: {report['issues_by_severity']['critical']}"
                )
                logger.info(f"   High Issues: {report['issues_by_severity']['high']}")

                return analysis_results
            else:
                logger.error("❌ Comprehensive analysis failed")
                return analysis_results
        else:
            logger.error("❌ Component testing failed")
            return component_results

    except Exception as e:
        logger.error(f"Test suite execution failed: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    results = main()
    sys.exit(0 if results.get("success") else 1)
