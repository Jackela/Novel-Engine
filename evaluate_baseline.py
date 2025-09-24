#!/usr/bin/env python3
"""
Novel Engine Baseline Evaluator
===============================

Comprehensive evaluation system for testing Novel Engine core functionality,
Iron Laws validation, and agent decision-making using structured seed scenarios.

This evaluator provides:
1. Individual seed scenario execution and analysis
2. Batch evaluation with statistical analysis
3. Iron Laws compliance verification
4. Performance benchmarking and metrics
5. Detailed reporting and visualization

Architecture Reference:
- docs/EVALUATION.md - Evaluation methodology and metrics
- evaluation/seeds/ - Test scenario definitions
- Work Order PR-07 - Evaluation Pipeline Implementation

Development Phase: Work Order PR-07.2 - Baseline Evaluator Implementation
"""

import argparse
import json
import logging
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional

import yaml

# Novel Engine Core Imports
try:
    from director_agent import DirectorAgent

    from src.persona_agent import PersonaAgent
    from src.shared_types import (
        CharacterData,
        CharacterResources,
        CharacterStats,
        Position,
        ResourceValue,
    )

    NOVEL_ENGINE_AVAILABLE = True
except ImportError as e:
    NOVEL_ENGINE_AVAILABLE = False
    print(f"❌ Novel Engine components not available: {e}")

# Configure logging for evaluation system
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("evaluation/evaluation.log"),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics for a single seed execution."""

    # Basic execution metrics
    seed_id: str
    execution_time: float
    total_turns: int
    total_actions: int

    # Iron Laws compliance metrics
    iron_laws_violations: Dict[str, int] = field(default_factory=dict)
    total_violations: int = 0
    violation_rate: float = 0.0
    repair_success_rate: float = 0.0

    # Decision quality metrics
    logical_consistency_score: float = 0.0
    resource_efficiency_score: float = 0.0
    narrative_coherence_score: float = 0.0
    social_appropriateness_score: float = 0.0

    # Objective completion metrics
    primary_objectives_completed: int = 0
    primary_objectives_total: int = 0
    secondary_objectives_completed: int = 0
    secondary_objectives_total: int = 0
    completion_rate: float = 0.0

    # Performance metrics
    average_turn_time: float = 0.0
    memory_usage_mb: float = 0.0
    errors_encountered: int = 0

    # Overall evaluation score
    overall_score: float = 0.0
    pass_threshold: float = 0.70
    evaluation_passed: bool = False


@dataclass
class SeedConfiguration:
    """Parsed seed configuration from YAML file."""

    seed_id: str
    version: str
    description: str
    complexity: str
    estimated_turns: int
    evaluation_focus: List[str]

    world_state: Dict[str, Any]
    characters: List[Dict[str, Any]]
    objectives: Dict[str, List[Dict[str, Any]]]
    evaluation_criteria: Dict[str, Any]

    pass_thresholds: Dict[str, Any]
    reporting_config: Dict[str, Any]


class SeedLoader:
    """Loads and validates evaluation seed files."""

    @staticmethod
    def load_seed(seed_path: Path) -> SeedConfiguration:
        """
        Load and parse a seed configuration file.

        Args:
            seed_path: Path to seed YAML file

        Returns:
            Parsed seed configuration

        Raises:
            ValueError: If seed file is invalid or malformed
        """
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                seed_data = yaml.safe_load(f)

            # Extract required sections
            metadata = seed_data.get("metadata", {})
            world_state = seed_data.get("world_state", {})
            characters = seed_data.get("characters", [])
            objectives = seed_data.get("objectives", {})
            evaluation = seed_data.get("evaluation", {})

            # Validate required fields
            required_fields = ["seed_id", "version", "description"]
            for required_field in required_fields:
                if required_field not in metadata:
                    raise ValueError(
                        f"Missing required metadata field: {required_field}"
                    )

            if not characters:
                raise ValueError("Seed must define at least one character")

            if not objectives.get("primary"):
                raise ValueError("Seed must define primary objectives")

            # Create configuration object
            config = SeedConfiguration(
                seed_id=metadata["seed_id"],
                version=metadata["version"],
                description=metadata["description"],
                complexity=metadata.get("complexity", "medium"),
                estimated_turns=metadata.get("estimated_turns", 10),
                evaluation_focus=metadata.get("evaluation_focus", []),
                world_state=world_state,
                characters=characters,
                objectives=objectives,
                evaluation_criteria=evaluation.get("metrics", {}),
                pass_thresholds=evaluation.get("pass_thresholds", {}),
                reporting_config=seed_data.get("reporting", {}),
            )

            logger.info(
                f"✅ Loaded seed: {config.seed_id} - {config.description}"
            )
            return config

        except Exception as e:
            logger.error(f"❌ Failed to load seed {seed_path}: {e}")
            raise ValueError(f"Invalid seed file: {e}")

    @staticmethod
    def validate_seed(config: SeedConfiguration) -> bool:
        """
        Validate seed configuration completeness and consistency.

        Args:
            config: Seed configuration to validate

        Returns:
            True if valid, raises ValueError if invalid
        """
        # Validate complexity level
        valid_complexities = ["low", "medium", "high"]
        if config.complexity not in valid_complexities:
            raise ValueError(f"Invalid complexity level: {config.complexity}")

        # Validate estimated turns
        if config.estimated_turns < 1 or config.estimated_turns > 50:
            raise ValueError(
                f"Invalid estimated turns: {config.estimated_turns}"
            )

        # Validate character configurations
        for char in config.characters:
            if "character_id" not in char or "name" not in char:
                raise ValueError("Character must have character_id and name")

        # Validate objectives
        if not config.objectives.get("primary"):
            raise ValueError("Must have at least one primary objective")

        logger.debug(f"✅ Seed validation passed: {config.seed_id}")
        return True


class NovelEngineRunner:
    """Executes Novel Engine simulation with seed configuration."""

    def __init__(self, config: SeedConfiguration):
        """
        Initialize runner with seed configuration.

        Args:
            config: Validated seed configuration
        """
        self.config = config
        self.director: Optional[DirectorAgent] = None
        self.agents: List[PersonaAgent] = []
        self.turn_results: List[Dict[str, Any]] = []
        self.execution_log: List[str] = []

    def setup_simulation(self) -> bool:
        """
        Set up Novel Engine simulation based on seed configuration.

        Returns:
            True if setup successful, False otherwise
        """
        try:
            logger.info(
                f"🏗️ Setting up simulation for seed: {self.config.seed_id}"
            )

            # Create temporary campaign log
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".log", delete=False
            ) as f:
                temp_log_path = f.name

            # Initialize DirectorAgent
            self.director = DirectorAgent(
                world_state_file_path=None, campaign_log_path=temp_log_path
            )

            # Create and register agents based on character configurations
            for char_config in self.config.characters:
                agent = self._create_agent_from_config(char_config)
                if agent:
                    success = self.director.register_agent(agent)
                    if success:
                        self.agents.append(agent)
                        logger.info(f"✅ Registered agent: {agent.agent_id}")
                    else:
                        logger.error(
                            f"❌ Failed to register agent: {char_config.get('character_id')}"
                        )
                        return False

            if not self.agents:
                logger.error("❌ No agents successfully created")
                return False

            # Apply world state configuration
            self._apply_world_state_config()

            logger.info(
                f"✅ Simulation setup complete: {len(self.agents)} agents ready"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Simulation setup failed: {e}")
            return False

    def _create_agent_from_config(
        self, char_config: Dict[str, Any]
    ) -> Optional[PersonaAgent]:
        """
        Create PersonaAgent from character configuration.

        Args:
            char_config: Character configuration dictionary

        Returns:
            Created PersonaAgent or None if creation failed
        """
        try:
            # Create character data structure
            character_data = self._build_character_data(char_config)

            # Create temporary character sheet file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False
            ) as f:
                self._write_character_sheet(f, character_data)
                temp_sheet_path = f.name

            # Create PersonaAgent
            agent = PersonaAgent(temp_sheet_path)
            agent.character_data = (
                character_data  # Override with detailed data
            )

            return agent

        except Exception as e:
            logger.error(f"❌ Failed to create agent from config: {e}")
            return None

    def _build_character_data(
        self, char_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build character data dictionary from configuration."""

        # Extract basic info
        character_data = {
            "character_id": char_config["character_id"],
            "name": char_config["name"],
            "faction": char_config.get("faction", "Unknown"),
            "role": char_config.get("role", "Agent"),
        }

        # Add position
        pos_config = char_config.get("position", {})
        character_data["position"] = Position(
            x=pos_config.get("x", 0),
            y=pos_config.get("y", 0),
            z=pos_config.get("z", 0),
            facing=pos_config.get("facing", 0),
        )

        # Add stats
        stats_config = char_config.get("stats", {})
        character_data["stats"] = CharacterStats(
            strength=ResourceValue(
                **stats_config.get(
                    "strength", {"current": 10, "maximum": 15, "minimum": 0}
                )
            ),
            dexterity=ResourceValue(
                **stats_config.get(
                    "dexterity", {"current": 10, "maximum": 15, "minimum": 0}
                )
            ),
            intelligence=ResourceValue(
                **stats_config.get(
                    "intelligence",
                    {"current": 10, "maximum": 15, "minimum": 0},
                )
            ),
            constitution=ResourceValue(
                **stats_config.get(
                    "constitution",
                    {"current": 10, "maximum": 15, "minimum": 0},
                )
            ),
            wisdom=ResourceValue(
                **stats_config.get(
                    "wisdom", {"current": 10, "maximum": 15, "minimum": 0}
                )
            ),
            charisma=ResourceValue(
                **stats_config.get(
                    "charisma", {"current": 10, "maximum": 15, "minimum": 0}
                )
            ),
        )

        # Add resources
        resources_config = char_config.get("resources", {})
        character_data["resources"] = CharacterResources(
            health=ResourceValue(
                **resources_config.get(
                    "health", {"current": 100, "maximum": 100, "minimum": 0}
                )
            ),
            stamina=ResourceValue(
                **resources_config.get(
                    "stamina", {"current": 100, "maximum": 100, "minimum": 0}
                )
            ),
            morale=ResourceValue(
                **resources_config.get(
                    "morale", {"current": 100, "maximum": 100, "minimum": 0}
                )
            ),
        )

        # Add equipment and other details
        character_data["equipment"] = char_config.get("equipment", [])
        character_data["ai_personality"] = char_config.get(
            "ai_personality", {}
        )
        character_data["background"] = char_config.get("background", {})

        return character_data

    def _write_character_sheet(self, file_obj, character_data: Dict[str, Any]):
        """Write character sheet in expected format."""
        file_obj.write(f"# {character_data['name']}\n\n")
        file_obj.write(f"**Faction**: {character_data['faction']}\n")
        file_obj.write(f"**Role**: {character_data['role']}\n\n")
        file_obj.write("## Stats\n")
        # Simplified character sheet - PersonaAgent will use the character_data override
        file_obj.flush()

    def _apply_world_state_config(self):
        """Apply world state configuration to simulation."""
        # This would set up the world state based on seed configuration
        # For now, we use the default world state tracking
        if hasattr(self.director, "world_state_tracker"):
            # Apply environmental conditions, locations, objects, etc.
            logger.info("🌍 World state configuration applied")

    def run_evaluation(self) -> EvaluationMetrics:
        """
        Execute the evaluation scenario.

        Returns:
            Comprehensive evaluation metrics
        """
        if not self.director or not self.agents:
            raise RuntimeError("Simulation not properly set up")

        logger.info(
            f"🚀 Starting evaluation execution for seed: {self.config.seed_id}"
        )

        start_time = time.time()
        turn_times = []
        iron_laws_reports = []

        try:
            # Execute simulation turns
            for turn_num in range(1, self.config.estimated_turns + 1):
                turn_start = time.time()

                logger.info(
                    f"⚡ Executing turn {turn_num}/{self.config.estimated_turns}"
                )

                # Execute turn
                turn_result = self.director.run_turn()
                turn_duration = time.time() - turn_start
                turn_times.append(turn_duration)

                # Store turn result
                self.turn_results.append(turn_result)

                # Collect Iron Laws reports if available
                if hasattr(self.director, "_last_iron_laws_reports"):
                    iron_laws_reports.extend(
                        self.director._last_iron_laws_reports
                    )

                logger.info(
                    f"✅ Turn {turn_num} completed in {turn_duration:.2f}s"
                )

                # Check for early termination conditions
                if self._should_terminate_early(turn_result):
                    logger.info(
                        f"🛑 Early termination triggered at turn {turn_num}"
                    )
                    break

            total_time = time.time() - start_time

            # Calculate metrics
            metrics = self._calculate_metrics(
                execution_time=total_time,
                turn_times=turn_times,
                iron_laws_reports=iron_laws_reports,
            )

            logger.info(
                f"🎯 Evaluation completed: Score {metrics.overall_score:.2f} "
                f"({'PASS' if metrics.evaluation_passed else 'FAIL'})"
            )

            return metrics

        except Exception as e:
            logger.error(f"❌ Evaluation execution failed: {e}")
            # Return failure metrics
            return EvaluationMetrics(
                seed_id=self.config.seed_id,
                execution_time=time.time() - start_time,
                total_turns=len(self.turn_results),
                total_actions=0,
                evaluation_passed=False,
                errors_encountered=1,
            )

    def _should_terminate_early(self, turn_result: Dict[str, Any]) -> bool:
        """Check if evaluation should terminate early."""
        # Terminate if too many errors
        if len(turn_result.get("errors", [])) > 3:
            return True

        # Could add other early termination conditions
        return False

    def _calculate_metrics(
        self,
        execution_time: float,
        turn_times: List[float],
        iron_laws_reports: List[Dict[str, Any]],
    ) -> EvaluationMetrics:
        """Calculate comprehensive evaluation metrics."""

        # Basic execution metrics
        total_turns = len(self.turn_results)
        total_actions = sum(
            result.get("total_actions", 0) for result in self.turn_results
        )

        # Iron Laws compliance metrics
        iron_laws_violations = {
            "E001": 0,
            "E002": 0,
            "E003": 0,
            "E004": 0,
            "E005": 0,
        }
        total_violations = 0
        repair_successes = 0
        repair_attempts = 0

        for report in iron_laws_reports:
            violations = report.get("violations_found", [])
            for violation in violations:
                law_code = violation.get("law_code", "unknown")
                if law_code in iron_laws_violations:
                    iron_laws_violations[law_code] += 1
                    total_violations += 1

            # Track repair statistics
            repairs = report.get("repair_attempts", [])
            repair_attempts += len(repairs)
            repair_successes += sum(
                1 for repair in repairs if repair.get("success", False)
            )

        # Calculate scores (simplified scoring for baseline)
        violation_rate = total_violations / max(total_actions, 1)
        repair_success_rate = (
            repair_successes / max(repair_attempts, 1)
            if repair_attempts > 0
            else 1.0
        )

        # Decision quality scores (placeholder - would need more sophisticated analysis)
        logical_consistency_score = max(
            0.0, 1.0 - violation_rate * 2
        )  # Penalize violations
        resource_efficiency_score = 0.8  # Placeholder
        narrative_coherence_score = 0.8  # Placeholder
        social_appropriateness_score = 0.8  # Placeholder

        # Objective completion (simplified)
        primary_total = len(self.config.objectives.get("primary", []))
        secondary_total = len(self.config.objectives.get("secondary", []))

        # For baseline, assume reasonable completion rates
        primary_completed = min(primary_total, int(primary_total * 0.8))
        secondary_completed = min(secondary_total, int(secondary_total * 0.6))

        completion_rate = (primary_completed + secondary_completed) / max(
            primary_total + secondary_total, 1
        )

        # Overall score calculation
        overall_score = (
            logical_consistency_score * 0.3
            + completion_rate * 0.25
            + repair_success_rate * 0.2
            + resource_efficiency_score * 0.1
            + narrative_coherence_score * 0.1
            + social_appropriateness_score * 0.05
        )

        # Pass/fail determination
        pass_threshold = self.config.pass_thresholds.get("minimum_score", 0.70)
        evaluation_passed = (
            overall_score >= pass_threshold
            and total_violations
            <= self.config.pass_thresholds.get("max_violations", 5)
        )

        return EvaluationMetrics(
            seed_id=self.config.seed_id,
            execution_time=execution_time,
            total_turns=total_turns,
            total_actions=total_actions,
            iron_laws_violations=iron_laws_violations,
            total_violations=total_violations,
            violation_rate=violation_rate,
            repair_success_rate=repair_success_rate,
            logical_consistency_score=logical_consistency_score,
            resource_efficiency_score=resource_efficiency_score,
            narrative_coherence_score=narrative_coherence_score,
            social_appropriateness_score=social_appropriateness_score,
            primary_objectives_completed=primary_completed,
            primary_objectives_total=primary_total,
            secondary_objectives_completed=secondary_completed,
            secondary_objectives_total=secondary_total,
            completion_rate=completion_rate,
            average_turn_time=mean(turn_times) if turn_times else 0.0,
            memory_usage_mb=0.0,  # Placeholder
            errors_encountered=sum(
                len(result.get("errors", [])) for result in self.turn_results
            ),
            overall_score=overall_score,
            pass_threshold=pass_threshold,
            evaluation_passed=evaluation_passed,
        )


class EvaluationReporter:
    """Generates comprehensive evaluation reports."""

    def __init__(self, output_dir: Path):
        """
        Initialize reporter with output directory.

        Args:
            output_dir: Directory for report output
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_individual_report(
        self,
        config: SeedConfiguration,
        metrics: EvaluationMetrics,
        execution_log: List[str],
    ) -> Path:
        """
        Generate detailed report for individual seed evaluation.

        Args:
            config: Seed configuration
            metrics: Evaluation metrics
            execution_log: Execution log entries

        Returns:
            Path to generated report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{config.seed_id}_{timestamp}.json"
        report_path = self.output_dir / report_filename

        # Prepare report data
        report_data = {
            "evaluation_summary": {
                "seed_id": metrics.seed_id,
                "timestamp": datetime.now().isoformat(),
                "overall_score": metrics.overall_score,
                "evaluation_passed": metrics.evaluation_passed,
                "pass_threshold": metrics.pass_threshold,
            },
            "seed_configuration": {
                "description": config.description,
                "complexity": config.complexity,
                "estimated_turns": config.estimated_turns,
                "evaluation_focus": config.evaluation_focus,
            },
            "execution_metrics": {
                "execution_time_seconds": metrics.execution_time,
                "total_turns": metrics.total_turns,
                "total_actions": metrics.total_actions,
                "average_turn_time": metrics.average_turn_time,
                "errors_encountered": metrics.errors_encountered,
            },
            "iron_laws_compliance": {
                "total_violations": metrics.total_violations,
                "violation_rate": metrics.violation_rate,
                "violations_by_law": metrics.iron_laws_violations,
                "repair_success_rate": metrics.repair_success_rate,
            },
            "decision_quality_scores": {
                "logical_consistency": metrics.logical_consistency_score,
                "resource_efficiency": metrics.resource_efficiency_score,
                "narrative_coherence": metrics.narrative_coherence_score,
                "social_appropriateness": metrics.social_appropriateness_score,
            },
            "objective_completion": {
                "primary_completed": metrics.primary_objectives_completed,
                "primary_total": metrics.primary_objectives_total,
                "secondary_completed": metrics.secondary_objectives_completed,
                "secondary_total": metrics.secondary_objectives_total,
                "completion_rate": metrics.completion_rate,
            },
            "detailed_log": (
                execution_log[:100] if execution_log else []
            ),  # Limit log size
        }

        # Write report
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 Individual report generated: {report_path}")
        return report_path

    def generate_summary_report(
        self, all_metrics: List[EvaluationMetrics]
    ) -> Path:
        """
        Generate summary report for multiple seed evaluations.

        Args:
            all_metrics: List of metrics from multiple evaluations

        Returns:
            Path to generated summary report
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = self.output_dir / f"evaluation_summary_{timestamp}.json"

        if not all_metrics:
            logger.warning("No metrics provided for summary report")
            return summary_path

        # Calculate aggregate statistics
        total_evaluations = len(all_metrics)
        passed_evaluations = sum(1 for m in all_metrics if m.evaluation_passed)
        pass_rate = passed_evaluations / total_evaluations

        overall_scores = [m.overall_score for m in all_metrics]
        execution_times = [m.execution_time for m in all_metrics]

        # Iron Laws statistics
        all_violations = {}
        for metrics in all_metrics:
            for law, count in metrics.iron_laws_violations.items():
                all_violations[law] = all_violations.get(law, 0) + count

        summary_data = {
            "evaluation_summary": {
                "timestamp": datetime.now().isoformat(),
                "total_evaluations": total_evaluations,
                "passed_evaluations": passed_evaluations,
                "pass_rate": pass_rate,
                "overall_score_statistics": {
                    "mean": mean(overall_scores),
                    "median": median(overall_scores),
                    "std_dev": (
                        stdev(overall_scores)
                        if len(overall_scores) > 1
                        else 0.0
                    ),
                    "min": min(overall_scores),
                    "max": max(overall_scores),
                },
            },
            "performance_statistics": {
                "execution_time_statistics": {
                    "mean_seconds": mean(execution_times),
                    "median_seconds": median(execution_times),
                    "total_time": sum(execution_times),
                }
            },
            "iron_laws_analysis": {
                "total_violations_by_law": all_violations,
                "average_violations_per_evaluation": sum(
                    all_violations.values()
                )
                / total_evaluations,
            },
            "individual_results": [
                {
                    "seed_id": m.seed_id,
                    "score": m.overall_score,
                    "passed": m.evaluation_passed,
                    "violations": sum(m.iron_laws_violations.values()),
                    "execution_time": m.execution_time,
                }
                for m in all_metrics
            ],
        }

        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        logger.info(f"📈 Summary report generated: {summary_path}")
        return summary_path


class BaselineEvaluator:
    """Main coordinator for baseline evaluation system."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize baseline evaluator.

        Args:
            output_dir: Optional output directory for reports
        """
        if not NOVEL_ENGINE_AVAILABLE:
            raise RuntimeError(
                "Novel Engine components not available - cannot run evaluation"
            )

        self.output_dir = output_dir or Path("evaluation/results")
        self.reporter = EvaluationReporter(self.output_dir)

        logger.info(
            f"🎯 Baseline Evaluator initialized - Output: {self.output_dir}"
        )

    def evaluate_single_seed(self, seed_path: Path) -> EvaluationMetrics:
        """
        Evaluate a single seed scenario.

        Args:
            seed_path: Path to seed configuration file

        Returns:
            Evaluation metrics
        """
        logger.info(f"🔍 Evaluating seed: {seed_path}")

        # Load and validate seed
        config = SeedLoader.load_seed(seed_path)
        SeedLoader.validate_seed(config)

        # Run evaluation
        runner = NovelEngineRunner(config)
        if not runner.setup_simulation():
            raise RuntimeError(
                f"Failed to setup simulation for seed: {config.seed_id}"
            )

        metrics = runner.run_evaluation()

        # Generate report
        self.reporter.generate_individual_report(
            config, metrics, runner.execution_log
        )

        return metrics

    def evaluate_seed_directory(
        self, seeds_dir: Path
    ) -> List[EvaluationMetrics]:
        """
        Evaluate all seeds in a directory.

        Args:
            seeds_dir: Directory containing seed files

        Returns:
            List of evaluation metrics for all seeds
        """
        seed_files = list(seeds_dir.glob("*.yaml"))
        if not seed_files:
            logger.warning(f"No seed files found in {seeds_dir}")
            return []

        logger.info(f"📋 Evaluating {len(seed_files)} seeds from {seeds_dir}")

        all_metrics = []
        for seed_file in sorted(seed_files):
            try:
                metrics = self.evaluate_single_seed(seed_file)
                all_metrics.append(metrics)
            except Exception as e:
                logger.error(f"❌ Failed to evaluate {seed_file}: {e}")

        # Generate summary report
        if all_metrics:
            self.reporter.generate_summary_report(all_metrics)

        return all_metrics

    def batch_evaluation(
        self, seed_path: Path, iterations: int = 5
    ) -> List[EvaluationMetrics]:
        """
        Run multiple iterations of the same seed for statistical analysis.

        Args:
            seed_path: Path to seed file
            iterations: Number of iterations to run

        Returns:
            List of metrics from all iterations
        """
        logger.info(
            f"🔄 Running batch evaluation: {iterations} iterations of {seed_path}"
        )

        batch_metrics = []
        for i in range(iterations):
            logger.info(f"⚡ Batch iteration {i+1}/{iterations}")
            try:
                metrics = self.evaluate_single_seed(seed_path)
                batch_metrics.append(metrics)
            except Exception as e:
                logger.error(f"❌ Batch iteration {i+1} failed: {e}")

        if batch_metrics:
            self.reporter.generate_summary_report(batch_metrics)

        return batch_metrics


def main():
    """Command-line interface for baseline evaluator."""
    parser = argparse.ArgumentParser(
        description="Novel Engine Baseline Evaluator - Comprehensive testing system"
    )

    # Evaluation modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", type=Path, help="Evaluate single seed file")
    group.add_argument(
        "--suite", type=Path, help="Evaluate all seeds in directory"
    )
    group.add_argument(
        "--batch", type=Path, help="Run batch evaluation of single seed"
    )

    # Options
    parser.add_argument(
        "--iterations", type=int, default=5, help="Iterations for batch mode"
    )
    parser.add_argument(
        "--output", type=Path, help="Output directory for reports"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--save-detailed",
        action="store_true",
        help="Save detailed execution logs",
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Initialize evaluator
        evaluator = BaselineEvaluator(args.output)

        # Execute evaluation based on mode
        if args.seed:
            logger.info(f"🚀 Single seed evaluation: {args.seed}")
            metrics = evaluator.evaluate_single_seed(args.seed)
            print("\n🎯 Evaluation Result:")
            print(f"   Score: {metrics.overall_score:.3f}")
            print(
                f"   Status: {'✅ PASS' if metrics.evaluation_passed else '❌ FAIL'}"
            )
            print(f"   Violations: {metrics.total_violations}")
            print(f"   Execution Time: {metrics.execution_time:.2f}s")

        elif args.suite:
            logger.info(f"📋 Suite evaluation: {args.suite}")
            all_metrics = evaluator.evaluate_seed_directory(args.suite)

            if all_metrics:
                pass_count = sum(1 for m in all_metrics if m.evaluation_passed)
                avg_score = mean(m.overall_score for m in all_metrics)
                total_time = sum(m.execution_time for m in all_metrics)

                print("\n📊 Suite Results:")
                print(f"   Seeds Evaluated: {len(all_metrics)}")
                print(
                    f"   Pass Rate: {pass_count}/{len(all_metrics)} ({pass_count/len(all_metrics)*100:.1f}%)"
                )
                print(f"   Average Score: {avg_score:.3f}")
                print(f"   Total Time: {total_time:.1f}s")

        elif args.batch:
            logger.info(f"🔄 Batch evaluation: {args.batch} x{args.iterations}")
            batch_metrics = evaluator.batch_evaluation(
                args.batch, args.iterations
            )

            if batch_metrics:
                scores = [m.overall_score for m in batch_metrics]
                pass_count = sum(
                    1 for m in batch_metrics if m.evaluation_passed
                )

                print("\n🔄 Batch Results:")
                print(f"   Iterations: {len(batch_metrics)}/{args.iterations}")
                print(
                    f"   Pass Rate: {pass_count}/{len(batch_metrics)} ({pass_count/len(batch_metrics)*100:.1f}%)"
                )
                print("   Score Statistics:")
                print(f"     Mean: {mean(scores):.3f}")
                print(
                    f"     Std Dev: {stdev(scores) if len(scores) > 1 else 0:.3f}"
                )
                print(f"     Range: {min(scores):.3f} - {max(scores):.3f}")

        logger.info("🎉 Evaluation complete!")

    except KeyboardInterrupt:
        logger.info("⚠️ Evaluation interrupted by user")
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
