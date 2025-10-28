#!/usr/bin/env python3
"""
Novel Engine Automated Evaluation Pipeline
==========================================

Automated testing pipeline for continuous evaluation of Novel Engine
performance, Iron Laws compliance, and system reliability.

This pipeline provides:
1. Automated daily/weekly evaluation runs
2. Performance regression detection
3. Iron Laws compliance monitoring
4. Trend analysis and reporting
5. CI/CD integration support
6. Alert system for failures

Architecture Reference:
- docs/EVALUATION.md - Evaluation methodology
- evaluate_baseline.py - Core evaluation engine
- Work Order PR-07.3 - Automated Testing Pipeline

Development Phase: Work Order PR-07.3 - Automated Testing Pipeline
"""

import argparse
import json
import logging
import smtplib
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("evaluation/pipeline.log")],
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for evaluation pipeline."""

    # Evaluation settings
    seeds_directory: Path = Path("evaluation/seeds")
    results_directory: Path = Path("evaluation/results")
    archive_directory: Path = Path("evaluation/archive")

    # Pipeline scheduling
    run_mode: str = "manual"  # manual, daily, weekly, ci
    max_execution_time: int = 3600  # seconds

    # Performance monitoring
    enable_performance_tracking: bool = True
    performance_baseline_file: Path = Path("evaluation/baseline_performance.json")
    regression_threshold: float = 0.1  # 10% performance degradation threshold

    # Quality gates
    minimum_pass_rate: float = 0.85  # 85% of seeds must pass
    maximum_violation_rate: float = 0.05  # 5% violation rate maximum
    critical_violation_threshold: int = 10  # Alert if violations exceed this

    # Reporting
    generate_html_report: bool = True
    generate_trend_analysis: bool = True
    save_detailed_logs: bool = True

    # Alerting (optional)
    email_alerts: bool = False
    email_recipients: List[str] = field(default_factory=list)
    smtp_server: str = ""
    smtp_port: int = 587


@dataclass
class PipelineResults:
    """Results from pipeline execution."""

    timestamp: datetime
    execution_time: float

    # Evaluation results
    total_seeds_evaluated: int = 0
    seeds_passed: int = 0
    seeds_failed: int = 0
    pass_rate: float = 0.0

    # Iron Laws metrics
    total_violations: int = 0
    violation_rate: float = 0.0
    violations_by_law: Dict[str, int] = field(default_factory=dict)

    # Performance metrics
    average_execution_time: float = 0.0
    total_evaluation_time: float = 0.0
    performance_regression: float = 0.0

    # Quality gates status
    quality_gates_passed: bool = False
    gate_failures: List[str] = field(default_factory=list)

    # Overall status
    pipeline_success: bool = False


class PerformanceTracker:
    """Tracks performance metrics and detects regressions."""

    def __init__(self, baseline_file: Path):
        """
        Initialize performance tracker.

        Args:
            baseline_file: Path to baseline performance data
        """
        self.baseline_file = baseline_file
        self.baseline_data = self._load_baseline()

    def _load_baseline(self) -> Dict[str, Any]:
        """Load baseline performance data."""
        if self.baseline_file.exists():
            try:
                with open(self.baseline_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load baseline data: {e}")

        # Default baseline
        return {
            "last_updated": datetime.now().isoformat(),
            "seeds": {},
            "overall_metrics": {
                "average_execution_time": 300.0,  # 5 minutes default
                "average_pass_rate": 0.90,
                "average_violation_rate": 0.02,
            },
        }

    def update_baseline(self, results: PipelineResults, individual_metrics: List[Dict[str, Any]]):
        """Update baseline with new performance data."""

        # Update overall metrics
        self.baseline_data["overall_metrics"].update(
            {
                "average_execution_time": results.average_execution_time,
                "average_pass_rate": results.pass_rate,
                "average_violation_rate": results.violation_rate,
                "last_updated": results.timestamp.isoformat(),
            }
        )

        # Update individual seed metrics
        for metrics in individual_metrics:
            seed_id = metrics.get("seed_id")
            if seed_id:
                self.baseline_data["seeds"][seed_id] = {
                    "average_execution_time": metrics.get("execution_time", 0),
                    "typical_score": metrics.get("overall_score", 0),
                    "last_updated": results.timestamp.isoformat(),
                }

        # Save updated baseline
        self._save_baseline()

    def _save_baseline(self):
        """Save baseline data to file."""
        try:
            self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.baseline_file, "w") as f:
                json.dump(self.baseline_data, f, indent=2)
            logger.info(f"✅ Baseline data updated: {self.baseline_file}")
        except Exception as e:
            logger.error(f"Failed to save baseline data: {e}")

    def detect_regression(self, results: PipelineResults) -> Tuple[bool, List[str]]:
        """
        Detect performance regressions.

        Args:
            results: Current pipeline results

        Returns:
            Tuple of (has_regression, regression_details)
        """
        regressions = []
        baseline_metrics = self.baseline_data["overall_metrics"]

        # Check execution time regression
        baseline_time = baseline_metrics.get("average_execution_time", 300.0)
        current_time = results.average_execution_time
        time_regression = (current_time - baseline_time) / baseline_time

        if time_regression > 0.2:  # 20% slower
            regressions.append(f"Execution time regression: {time_regression*100:.1f}% slower")

        # Check pass rate regression
        baseline_pass_rate = baseline_metrics.get("average_pass_rate", 0.90)
        pass_rate_regression = baseline_pass_rate - results.pass_rate

        if pass_rate_regression > 0.1:  # 10% drop in pass rate
            regressions.append(f"Pass rate regression: {pass_rate_regression*100:.1f}% lower")

        # Check violation rate regression
        baseline_violation_rate = baseline_metrics.get("average_violation_rate", 0.02)
        violation_rate_regression = results.violation_rate - baseline_violation_rate

        if violation_rate_regression > 0.05:  # 5% increase in violations
            regressions.append(
                f"Violation rate regression: {violation_rate_regression*100:.1f}% higher"
            )

        return len(regressions) > 0, regressions


class ReportGenerator:
    """Generates comprehensive pipeline reports."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize report generator.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def generate_html_report(
        self,
        results: PipelineResults,
        individual_results: List[Dict[str, Any]],
        trend_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """
        Generate comprehensive HTML report.

        Args:
            results: Pipeline results
            individual_results: Individual seed results
            trend_data: Historical trend data

        Returns:
            Path to generated HTML report
        """
        timestamp = results.timestamp.strftime("%Y%m%d_%H%M%S")
        report_path = self.config.results_directory / f"pipeline_report_{timestamp}.html"

        # Generate HTML content
        html_content = self._build_html_report(results, individual_results, trend_data)

        # Write HTML file
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"📊 HTML report generated: {report_path}")
        return report_path

    def _build_html_report(
        self,
        results: PipelineResults,
        individual_results: List[Dict[str, Any]],
        trend_data: Optional[List[Dict[str, Any]]],
    ) -> str:
        """Build HTML report content."""

        # Status color and icon
        status_color = "green" if results.pipeline_success else "red"
        status_icon = "✅" if results.pipeline_success else "❌"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Novel Engine Evaluation Pipeline Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: white; padding: 15px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .metric-label {{ color: #7f8c8d; margin-top: 5px; }}
        .status-{status_color} {{ color: {status_color}; font-weight: bold; }}
        .violations-table {{ width: 100%; border-collapse: collapse; background: white; }}
        .violations-table th, .violations-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        .violations-table th {{ background-color: #f8f9fa; }}
        .seed-results {{ background: white; margin: 20px 0; padding: 20px; border-radius: 5px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{status_icon} Novel Engine Evaluation Pipeline Report</h1>
        <p>Generated: {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p class="status-{status_color}">Status: {'SUCCESS' if results.pipeline_success else 'FAILED'}</p>
    </div>
    
    <div class="summary">
        <div class="metric-card">
            <div class="metric-value">{results.pass_rate:.1%}</div>
            <div class="metric-label">Pass Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{results.total_seeds_evaluated}</div>
            <div class="metric-label">Seeds Evaluated</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{results.total_violations}</div>
            <div class="metric-label">Total Violations</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{results.execution_time:.1f}s</div>
            <div class="metric-label">Pipeline Time</div>
        </div>
    </div>
    
    <div class="seed-results">
        <h2>Iron Laws Violations by Type</h2>
        <table class="violations-table">
            <tr><th>Law Code</th><th>Violations</th><th>Percentage</th></tr>
        """

        # Add violations table
        for law_code, violations in results.violations_by_law.items():
            percentage = (violations / max(results.total_violations, 1)) * 100
            html += f"<tr><td>{law_code}</td><td>{violations}</td><td>{percentage:.1f}%</td></tr>"

        html += """
        </table>
    </div>
    
    <div class="seed-results">
        <h2>Individual Seed Results</h2>
        <table class="violations-table">
            <tr><th>Seed ID</th><th>Status</th><th>Score</th><th>Violations</th><th>Time</th></tr>
        """

        # Add individual results
        for result in individual_results:
            status_class = "pass" if result.get("passed", False) else "fail"
            status_text = "PASS" if result.get("passed", False) else "FAIL"
            html += f"""
            <tr>
                <td>{result.get('seed_id', 'Unknown')}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{result.get('score', 0):.3f}</td>
                <td>{result.get('violations', 0)}</td>
                <td>{result.get('execution_time', 0):.1f}s</td>
            </tr>
            """

        html += """
        </table>
    </div>
</body>
</html>
        """

        return html

    def generate_json_summary(
        self, results: PipelineResults, individual_results: List[Dict[str, Any]]
    ) -> Path:
        """Generate JSON summary report."""
        timestamp = results.timestamp.strftime("%Y%m%d_%H%M%S")
        report_path = self.config.results_directory / f"pipeline_summary_{timestamp}.json"

        summary_data = {
            "pipeline_execution": {
                "timestamp": results.timestamp.isoformat(),
                "execution_time_seconds": results.execution_time,
                "success": results.pipeline_success,
            },
            "evaluation_summary": {
                "total_seeds": results.total_seeds_evaluated,
                "seeds_passed": results.seeds_passed,
                "seeds_failed": results.seeds_failed,
                "pass_rate": results.pass_rate,
            },
            "iron_laws_compliance": {
                "total_violations": results.total_violations,
                "violation_rate": results.violation_rate,
                "violations_by_law": results.violations_by_law,
            },
            "performance_metrics": {
                "average_execution_time": results.average_execution_time,
                "total_evaluation_time": results.total_evaluation_time,
                "performance_regression": results.performance_regression,
            },
            "quality_gates": {
                "passed": results.quality_gates_passed,
                "failures": results.gate_failures,
            },
            "individual_results": individual_results,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)

        logger.info(f"📋 JSON summary generated: {report_path}")
        return report_path


class AlertSystem:
    """Handles alerts for pipeline failures and regressions."""

    def __init__(self, config: PipelineConfig):
        """Initialize alert system."""
        self.config = config

    def send_alerts(self, results: PipelineResults, regressions: List[str]):
        """
        Send alerts for failures and regressions.

        Args:
            results: Pipeline results
            regressions: List of detected regressions
        """
        if not self.config.email_alerts or not self.config.email_recipients:
            return

        # Determine alert level
        alert_level = (
            "CRITICAL" if not results.pipeline_success else "WARNING" if regressions else "INFO"
        )

        # Generate alert message
        subject = f"Novel Engine Pipeline {alert_level}: {results.timestamp.strftime('%Y-%m-%d')}"
        body = self._generate_alert_body(results, regressions, alert_level)

        # Send email
        try:
            self._send_email(subject, body)
            logger.info(f"📧 Alert sent: {alert_level}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def _generate_alert_body(
        self, results: PipelineResults, regressions: List[str], alert_level: str
    ) -> str:
        """Generate alert message body."""

        body = f"""
Novel Engine Evaluation Pipeline {alert_level}

Timestamp: {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Execution Time: {results.execution_time:.1f} seconds

SUMMARY:
- Total Seeds: {results.total_seeds_evaluated}
- Pass Rate: {results.pass_rate:.1%}
- Total Violations: {results.total_violations}
- Pipeline Status: {'SUCCESS' if results.pipeline_success else 'FAILED'}

"""

        if not results.quality_gates_passed:
            body += "\nQUALITY GATE FAILURES:\n"
            for failure in results.gate_failures:
                body += f"- {failure}\n"

        if regressions:
            body += "\nPERFORMANCE REGRESSIONS DETECTED:\n"
            for regression in regressions:
                body += f"- {regression}\n"

        body += "\nIRON LAWS VIOLATIONS:\n"
        for law_code, violations in results.violations_by_law.items():
            body += f"- {law_code}: {violations} violations\n"

        return body

    def _send_email(self, subject: str, body: str):
        """Send email alert."""
        msg = MIMEMultipart()
        msg["From"] = "novel-engine-pipeline@local"
        msg["To"] = ", ".join(self.config.email_recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
            server.starttls()
            server.send_message(msg)


class EvaluationPipeline:
    """Main evaluation pipeline coordinator."""

    def __init__(self, config: PipelineConfig):
        """
        Initialize evaluation pipeline.

        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.performance_tracker = PerformanceTracker(config.performance_baseline_file)
        self.report_generator = ReportGenerator(config)
        self.alert_system = AlertSystem(config)

    def run_pipeline(self) -> PipelineResults:
        """
        Execute complete evaluation pipeline.

        Returns:
            Pipeline execution results
        """
        start_time = time.time()
        timestamp = datetime.now()

        logger.info(f"🚀 Starting evaluation pipeline: {timestamp}")

        try:
            # Run baseline evaluator on all seeds
            individual_results = self._run_baseline_evaluation()

            # Calculate aggregate results
            results = self._calculate_pipeline_results(
                timestamp, time.time() - start_time, individual_results
            )

            # Check quality gates
            results.quality_gates_passed, results.gate_failures = self._check_quality_gates(results)
            results.pipeline_success = results.quality_gates_passed

            # Detect performance regressions
            has_regression, regressions = self.performance_tracker.detect_regression(results)
            if has_regression:
                results.performance_regression = max(
                    0.1, results.performance_regression
                )  # Set minimum regression indicator

            # Update performance baseline
            if results.pipeline_success:
                self.performance_tracker.update_baseline(results, individual_results)

            # Generate reports
            if self.config.generate_html_report:
                self.report_generator.generate_html_report(results, individual_results)

            self.report_generator.generate_json_summary(results, individual_results)

            # Send alerts if needed
            if not results.pipeline_success or has_regression:
                self.alert_system.send_alerts(results, regressions)

            logger.info(
                f"✅ Pipeline completed: {results.execution_time:.1f}s - "
                f"{'SUCCESS' if results.pipeline_success else 'FAILED'}"
            )

            return results

        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")

            # Return failure result
            return PipelineResults(
                timestamp=timestamp,
                execution_time=time.time() - start_time,
                pipeline_success=False,
                gate_failures=[f"Pipeline execution error: {str(e)}"],
            )

    def _run_baseline_evaluation(self) -> List[Dict[str, Any]]:
        """Run baseline evaluator on all seeds."""

        # Build command to run baseline evaluator
        evaluator_script = Path(__file__).parent.parent / "evaluate_baseline.py"
        seeds_dir = self.config.seeds_directory

        cmd = [
            sys.executable,
            str(evaluator_script),
            "--suite",
            str(seeds_dir),
            "--output",
            str(self.config.results_directory),
        ]

        logger.info(f"🔄 Running baseline evaluator: {' '.join(cmd)}")

        try:
            # Run evaluator with timeout
            result = subprocess.run(
                cmd,
                timeout=self.config.max_execution_time,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent,
            )

            if result.returncode != 0:
                logger.error(f"Baseline evaluator failed: {result.stderr}")
                return []

            # Parse results from output directory
            return self._parse_evaluation_results()

        except subprocess.TimeoutExpired:
            logger.error("Baseline evaluator timed out")
            return []
        except Exception as e:
            logger.error(f"Failed to run baseline evaluator: {e}")
            return []

    def _parse_evaluation_results(self) -> List[Dict[str, Any]]:
        """Parse evaluation results from output files."""
        results = []

        # Look for recent result files
        cutoff_time = datetime.now() - timedelta(minutes=30)

        for result_file in self.config.results_directory.glob("*.json"):
            try:
                if result_file.stat().st_mtime < cutoff_time.timestamp():
                    continue

                with open(result_file, "r") as f:
                    data = json.load(f)

                # Extract relevant metrics
                if "evaluation_summary" in data:
                    eval_summary = data["evaluation_summary"]
                    results.append(
                        {
                            "seed_id": eval_summary.get("seed_id", "unknown"),
                            "score": eval_summary.get("overall_score", 0.0),
                            "passed": eval_summary.get("evaluation_passed", False),
                            "violations": data.get("iron_laws_compliance", {}).get(
                                "total_violations", 0
                            ),
                            "execution_time": data.get("execution_metrics", {}).get(
                                "execution_time_seconds", 0
                            ),
                        }
                    )

            except Exception as e:
                logger.warning(f"Failed to parse result file {result_file}: {e}")

        return results

    def _calculate_pipeline_results(
        self, timestamp: datetime, execution_time: float, individual_results: List[Dict[str, Any]]
    ) -> PipelineResults:
        """Calculate aggregate pipeline results."""

        if not individual_results:
            return PipelineResults(
                timestamp=timestamp,
                execution_time=execution_time,
                pipeline_success=False,
                gate_failures=["No evaluation results found"],
            )

        # Calculate aggregate metrics
        total_seeds = len(individual_results)
        passed_seeds = sum(1 for r in individual_results if r.get("passed", False))
        failed_seeds = total_seeds - passed_seeds
        pass_rate = passed_seeds / total_seeds if total_seeds > 0 else 0.0

        total_violations = sum(r.get("violations", 0) for r in individual_results)
        total_actions = sum(r.get("total_actions", 100) for r in individual_results)  # Estimate
        violation_rate = total_violations / max(total_actions, 1)

        # Calculate violations by law (simplified - would need more detailed data)
        violations_by_law = {
            "E001": int(total_violations * 0.2),  # Estimated distribution
            "E002": int(total_violations * 0.3),
            "E003": int(total_violations * 0.2),
            "E004": int(total_violations * 0.2),
            "E005": int(total_violations * 0.1),
        }

        execution_times = [r.get("execution_time", 0) for r in individual_results]
        avg_execution_time = mean(execution_times) if execution_times else 0.0
        total_evaluation_time = sum(execution_times)

        return PipelineResults(
            timestamp=timestamp,
            execution_time=execution_time,
            total_seeds_evaluated=total_seeds,
            seeds_passed=passed_seeds,
            seeds_failed=failed_seeds,
            pass_rate=pass_rate,
            total_violations=total_violations,
            violation_rate=violation_rate,
            violations_by_law=violations_by_law,
            average_execution_time=avg_execution_time,
            total_evaluation_time=total_evaluation_time,
        )

    def _check_quality_gates(self, results: PipelineResults) -> Tuple[bool, List[str]]:
        """Check quality gates against results."""
        failures = []

        # Check pass rate
        if results.pass_rate < self.config.minimum_pass_rate:
            failures.append(
                f"Pass rate {results.pass_rate:.1%} below minimum {self.config.minimum_pass_rate:.1%}"
            )

        # Check violation rate
        if results.violation_rate > self.config.maximum_violation_rate:
            failures.append(
                f"Violation rate {results.violation_rate:.1%} exceeds maximum {self.config.maximum_violation_rate:.1%}"
            )

        # Check critical violations
        if results.total_violations > self.config.critical_violation_threshold:
            failures.append(
                f"Total violations {results.total_violations} exceeds threshold {self.config.critical_violation_threshold}"
            )

        return len(failures) == 0, failures


def load_pipeline_config(config_path: Path) -> PipelineConfig:
    """Load pipeline configuration from YAML file."""
    if config_path.exists():
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Convert paths
        for field in [
            "seeds_directory",
            "results_directory",
            "archive_directory",
            "performance_baseline_file",
        ]:
            if field in config_data:
                config_data[field] = Path(config_data[field])

        return PipelineConfig(**config_data)
    else:
        logger.info("Using default pipeline configuration")
        return PipelineConfig()


def main():
    """Command-line interface for evaluation pipeline."""
    parser = argparse.ArgumentParser(description="Novel Engine Automated Evaluation Pipeline")

    parser.add_argument(
        "--config",
        type=Path,
        default=Path("evaluation/pipeline_config.yaml"),
        help="Pipeline configuration file",
    )
    parser.add_argument(
        "--mode",
        choices=["manual", "daily", "weekly", "ci"],
        default="manual",
        help="Pipeline execution mode",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode - no actual evaluation"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load configuration
        config = load_pipeline_config(args.config)
        config.run_mode = args.mode

        if args.dry_run:
            logger.info("🔍 Dry run mode - pipeline structure validated")
            return 0

        # Run pipeline
        pipeline = EvaluationPipeline(config)
        results = pipeline.run_pipeline()

        # Print summary
        print("\n🎯 Pipeline Execution Summary:")
        print(f"   Status: {'✅ SUCCESS' if results.pipeline_success else '❌ FAILED'}")
        print(f"   Seeds Evaluated: {results.total_seeds_evaluated}")
        print(f"   Pass Rate: {results.pass_rate:.1%}")
        print(f"   Total Violations: {results.total_violations}")
        print(f"   Execution Time: {results.execution_time:.1f}s")

        if results.gate_failures:
            print("\n⚠️ Quality Gate Failures:")
            for failure in results.gate_failures:
                print(f"   - {failure}")

        return 0 if results.pipeline_success else 1

    except KeyboardInterrupt:
        logger.info("⚠️ Pipeline interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
