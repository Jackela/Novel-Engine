"""
Experiment Router Service

Warzone 4: AI Brain - BRAIN-018B
Service layer for experiment API router.

Constitution Compliance:
- Article II (Hexagonal): Application service uses port, doesn't use infrastructure directly
- Article I (DDD): Business logic for experiment operations
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional

from src.contexts.knowledge.application.ports.i_experiment_repository import (
    ExperimentNotFoundError,
    IExperimentRepository,
)
from src.contexts.knowledge.application.ports.i_prompt_repository import (
    IPromptRepository,
    PromptNotFoundError,
)
from src.contexts.knowledge.domain.models.prompt_experiment import (
    ExperimentMetric,
    ExperimentStatus,
    PromptExperiment,
)

logger = logging.getLogger(__name__)


def _sanitize_float_for_json(value: Any) -> Any:
    """
    Sanitize float values for JSON serialization.

    Replaces inf/-inf with 0.0 for JSON and schema compatibility.

    Args:
        value: Value to sanitize

    Returns:
        Sanitized value safe for JSON encoding
    """
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            return 0.0
    return value


def _sanitize_dict_for_json(data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively sanitize a dictionary for JSON serialization.

    Args:
        data: Dictionary to sanitize

    Returns:
        Sanitized dictionary safe for JSON encoding
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = _sanitize_dict_for_json(value)
        elif isinstance(value, list):
            result[key] = [_sanitize_float_for_json(v) for v in value]
        else:
            result[key] = _sanitize_float_for_json(value)
    return result


def _calculate_z_score(p: float, n: int) -> float:
    """
    Calculate the z-score for a proportion.

    Uses the Wilson score interval which is more accurate for proportions
    near 0 or 1 compared to the normal approximation.

    Args:
        p: Proportion (success rate)
        n: Sample size

    Returns:
        Z-score for the proportion
    """
    if n == 0:
        return 0.0

    # Standard error for proportion
    se = math.sqrt((p * (1 - p)) / n)

    if se == 0:
        return 0.0

    return 1.96 * se  # 1.96 is the z-value for 95% confidence


def _calculate_two_proportion_z_test(
    p1: float, n1: int, p2: float, n2: int
) -> dict[str, Any]:
    """
    Calculate two-proportion z-test for comparing success rates.

    Args:
        p1: Proportion for group 1
        n1: Sample size for group 1
        p2: Proportion for group 2
        n2: Sample size for group 2

    Returns:
        Dictionary with z-statistic, p-value, and confidence interval
    """
    if n1 == 0 or n2 == 0:
        return {
            "z_statistic": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "confidence_interval": None,
        }

    # Pooled proportion
    p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)

    # Standard error
    se = math.sqrt(p_pooled * (1 - p_pooled) * (1 / n1 + 1 / n2))

    if se == 0:
        return {
            "z_statistic": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "confidence_interval": None,
        }

    # Z-statistic
    z_statistic = (p1 - p2) / se

    # Two-tailed p-value (approximation using standard normal CDF)
    # Using the error function approximation
    abs_z = abs(z_statistic)
    p_value = 2 * (1 - _normal_cdf(abs_z))

    return {
        "z_statistic": round(z_statistic, 4),
        "p_value": round(p_value, 4),
        "is_significant": p_value < 0.05,  # 5% significance level
        "confidence_interval": None,  # Can be added if needed
    }


def _normal_cdf(x: float) -> float:
    """
    Calculate the cumulative distribution function for standard normal.

    Uses the error function approximation.

    Args:
        x: Value to calculate CDF for

    Returns:
        CDF value
    """
    # Abramowitz and Stegun approximation for erf
    sign = 1 if x >= 0 else -1
    x = abs(x) / math.sqrt(2)

    # Constants for approximation
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)

    return 0.5 * (1.0 + sign * y)


def _calculate_confidence_interval(
    value: float, n: int, confidence: float = 0.95
) -> dict[str, float]:
    """
    Calculate confidence interval for a proportion.

    Args:
        value: Observed proportion
        n: Sample size
        confidence: Confidence level (default 0.95 for 95%)

    Returns:
        Dictionary with lower and upper bounds
    """
    if n == 0:
        return {"lower": 0.0, "upper": 0.0}

    # Z-value for confidence level
    z_values = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_values.get(confidence, 1.96)

    # Standard error
    se = math.sqrt((value * (1 - value)) / n)

    # Margin of error
    margin = z * se

    return {
        "lower": max(0.0, value - margin),
        "upper": min(1.0, value + margin),
    }


class ExperimentRouterService:
    """
    Service layer for experiment router operations.

    Why:
        - Separates HTTP concerns from business logic
        - Provides reusable methods for router handlers
        - Handles entity-to-response conversions
        - Calculates statistical significance

    Attributes:
        _repository: The experiment repository port
        _prompt_repository: The prompt repository port (for validation)
    """

    def __init__(
        self,
        repository: IExperimentRepository,
        prompt_repository: IPromptRepository,
    ) -> None:
        """
        Initialize the experiment router service.

        Args:
            repository: Experiment repository implementing IExperimentRepository
            prompt_repository: Prompt repository for validating prompt IDs
        """
        self._repository = repository
        self._prompt_repository = prompt_repository

    async def create_experiment(
        self,
        name: str,
        prompt_a_id: str,
        prompt_b_id: str,
        metric: ExperimentMetric,
        traffic_split: int = 50,
        description: str = "",
        min_sample_size: int = 100,
        confidence_threshold: float = 0.95,
        created_by: Optional[str] = None,
    ) -> PromptExperiment:
        """
        Create a new experiment.

        Args:
            name: Experiment name
            prompt_a_id: Variant A prompt ID
            prompt_b_id: Variant B prompt ID
            metric: Primary metric for comparison
            traffic_split: Traffic split percentage for variant A
            description: Experiment description
            min_sample_size: Minimum sample size
            confidence_threshold: Statistical confidence threshold
            created_by: Optional creator identifier

        Returns:
            Created experiment

        Raises:
            PromptNotFoundError: If either prompt ID is invalid
            ValueError: If prompts are the same
        """
        # Validate prompt IDs
        prompt_a = await self._prompt_repository.get_by_id(prompt_a_id)
        if prompt_a is None:
            raise PromptNotFoundError(f"Prompt A '{prompt_a_id}' not found")

        prompt_b = await self._prompt_repository.get_by_id(prompt_b_id)
        if prompt_b is None:
            raise PromptNotFoundError(f"Prompt B '{prompt_b_id}' not found")

        # Create experiment
        experiment = PromptExperiment.create(
            name=name,
            prompt_a_id=prompt_a_id,
            prompt_b_id=prompt_b_id,
            metric=metric,
            traffic_split=traffic_split,
            description=description,
            min_sample_size=min_sample_size,
            confidence_threshold=confidence_threshold,
            created_by=created_by,
        )

        await self._repository.save(experiment)
        return experiment

    async def get_experiment(self, experiment_id: str) -> PromptExperiment:
        """
        Get an experiment by ID.

        Args:
            experiment_id: Experiment ID

        Returns:
            The experiment

        Raises:
            ExperimentNotFoundError: If experiment not found
        """
        experiment = await self._repository.get_by_id(experiment_id)
        if experiment is None:
            raise ExperimentNotFoundError(experiment_id)
        return experiment

    async def list_experiments(
        self,
        status: Optional[str] = None,
        prompt_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptExperiment]:
        """
        List experiments with optional filtering.

        Args:
            status: Optional filter by status
            prompt_id: Optional filter by prompt ID
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of experiments
        """
        return await self._repository.list_all(
            status=status, prompt_id=prompt_id, limit=limit, offset=offset
        )

    async def start_experiment(self, experiment_id: str) -> PromptExperiment:
        """
        Start an experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Updated experiment

        Raises:
            ExperimentNotFoundError: If experiment not found
            ValueError: If experiment is not in DRAFT status
        """
        experiment = await self.get_experiment(experiment_id)
        experiment.start()
        await self._repository.save(experiment)
        return experiment

    async def pause_experiment(self, experiment_id: str) -> PromptExperiment:
        """
        Pause a running experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Updated experiment

        Raises:
            ExperimentNotFoundError: If experiment not found
            ValueError: If experiment is not RUNNING
        """
        experiment = await self.get_experiment(experiment_id)
        experiment.pause()
        await self._repository.save(experiment)
        return experiment

    async def resume_experiment(self, experiment_id: str) -> PromptExperiment:
        """
        Resume a paused experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            Updated experiment

        Raises:
            ExperimentNotFoundError: If experiment not found
            ValueError: If experiment is not PAUSED
        """
        experiment = await self.get_experiment(experiment_id)
        experiment.resume()
        await self._repository.save(experiment)
        return experiment

    async def complete_experiment(
        self, experiment_id: str, winner_id: Optional[str] = None
    ) -> PromptExperiment:
        """
        Complete an experiment and optionally declare a winner.

        Args:
            experiment_id: Experiment ID
            winner_id: Optional winning variant ID

        Returns:
            Updated experiment

        Raises:
            ExperimentNotFoundError: If experiment not found
            ValueError: If experiment is not RUNNING/PAUSED
        """
        experiment = await self.get_experiment(experiment_id)
        experiment.complete(winner_id=winner_id)
        await self._repository.save(experiment)
        return experiment

    async def delete_experiment(self, experiment_id: str) -> bool:
        """
        Delete an experiment.

        Args:
            experiment_id: Experiment ID

        Returns:
            True if deleted, False if not found
        """
        return await self._repository.delete(experiment_id)

    async def record_result(
        self,
        experiment_id: str,
        variant_id: str,
        success: bool,
        tokens: int = 0,
        latency_ms: float = 0.0,
        rating: Optional[float] = None,
    ) -> PromptExperiment:
        """
        Record a generation result for an experiment.

        Args:
            experiment_id: Experiment ID
            variant_id: The variant used (prompt_a_id or prompt_b_id)
            success: Whether generation was successful
            tokens: Tokens consumed
            latency_ms: Response time in ms
            rating: Optional user rating

        Returns:
            Updated experiment

        Raises:
            ExperimentNotFoundError: If experiment not found
            ValueError: If variant_id is invalid
        """
        experiment = await self.get_experiment(experiment_id)

        if success:
            experiment.record_success(variant_id, tokens, latency_ms, rating)
        else:
            experiment.record_failure(variant_id, tokens, latency_ms)

        await self._repository.save(experiment)
        return experiment

    async def get_results(self, experiment_id: str) -> dict[str, Any]:
        """
        Get experiment results with statistical analysis.

        Args:
            experiment_id: Experiment ID

        Returns:
            Results dictionary with metrics, comparison, and significance

        Raises:
            ExperimentNotFoundError: If experiment not found
        """
        experiment = await self.get_experiment(experiment_id)

        # Get basic results
        results = experiment.get_results()

        # Add statistical significance analysis
        results["statistical_significance"] = self._calculate_significance(experiment)

        # Add confidence intervals for each variant
        results["variant_a"]["confidence_interval"] = _calculate_confidence_interval(
            experiment.metrics_a.success_rate / 100,
            experiment.metrics_a.total_runs,
            experiment.confidence_threshold,
        )
        results["variant_b"]["confidence_interval"] = _calculate_confidence_interval(
            experiment.metrics_b.success_rate / 100,
            experiment.metrics_b.total_runs,
            experiment.confidence_threshold,
        )

        # Sanitize infinity values for JSON serialization
        return _sanitize_dict_for_json(results)

    def _calculate_significance(self, experiment: PromptExperiment) -> dict[str, Any]:
        """
        Calculate statistical significance for experiment results.

        Args:
            experiment: The experiment to analyze

        Returns:
            Dictionary with significance metrics
        """
        n1 = experiment.metrics_a.total_runs
        n2 = experiment.metrics_b.total_runs
        p1 = experiment.metrics_a.success_rate / 100
        p2 = experiment.metrics_b.success_rate / 100

        # Check minimum sample size
        meets_min_sample = (
            n1 >= experiment.min_sample_size and n2 >= experiment.min_sample_size
        )

        # Calculate two-proportion z-test
        z_test = _calculate_two_proportion_z_test(p1, n1, p2, n2)

        # Calculate effect size (Cohen's h for proportions)
        # Cohen's h = 2 * arcsin(sqrt(p1)) - 2 * arcsin(sqrt(p2))
        def _cohens_h(prop1: float, prop2: float) -> float:
            try:
                return 2 * (math.asin(math.sqrt(prop1)) - math.asin(math.sqrt(prop2)))
            except (ValueError, ZeroDivisionError):
                return 0.0

        effect_size = _cohens_h(p1, p2)

        # Interpret effect size
        effect_interpretation = "negligible"
        if abs(effect_size) >= 0.5:
            effect_interpretation = "medium"
        if abs(effect_size) >= 0.8:
            effect_interpretation = "large"

        # Determine if we can declare a winner
        can_declare_winner = (
            meets_min_sample
            and z_test["is_significant"]
            and experiment.status == ExperimentStatus.RUNNING
        )

        return {
            "meets_minimum_sample_size": meets_min_sample,
            "minimum_sample_size_required": experiment.min_sample_size,
            "two_proportion_z_test": z_test,
            "effect_size": {
                "cohens_h": round(effect_size, 4),
                "interpretation": effect_interpretation,
            },
            "confidence_level": f"{experiment.confidence_threshold * 100:.0f}%",
            "can_declare_winner": can_declare_winner,
            "recommendation": self._get_recommendation(
                experiment, z_test, meets_min_sample
            ),
        }

    def _get_recommendation(
        self,
        experiment: PromptExperiment,
        z_test: dict[str, Any],
        meets_min_sample: bool,
    ) -> str:
        """
        Get recommendation based on statistical analysis.

        Args:
            experiment: The experiment
            z_test: Z-test results
            meets_min_sample: Whether minimum sample size is met

        Returns:
            Recommendation string
        """
        if not meets_min_sample:
            return (
                f"Collect more data. Need at least {experiment.min_sample_size} "
                f"runs per variant (current: {experiment.metrics_a.total_runs} vs "
                f"{experiment.metrics_b.total_runs})"
            )

        if not z_test["is_significant"]:
            return "No significant difference detected yet. Continue collecting data."

        # Significant difference detected
        if experiment.metrics_a.success_rate > experiment.metrics_b.success_rate:
            return "Variant A shows statistically significant improvement. Consider completing experiment."
        else:
            return "Variant B shows statistically significant improvement. Consider completing experiment."

    async def count_experiments(self) -> int:
        """
        Count total experiments.

        Returns:
            Total count
        """
        return await self._repository.count()

    def to_summary(self, experiment: PromptExperiment) -> dict[str, Any]:
        """
        Convert experiment to summary dictionary.

        Args:
            experiment: Prompt experiment entity

        Returns:
            Summary dictionary for API response
        """
        return {
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description,
            "status": experiment.status.value,
            "metric": experiment.metric.value,
            "prompt_a_id": experiment.prompt_a_id,
            "prompt_b_id": experiment.prompt_b_id,
            "traffic_split": experiment.traffic_split,
            "winner": (
                "A"
                if experiment.winner == experiment.prompt_a_id
                else (
                    "B"
                    if experiment.winner == experiment.prompt_b_id
                    else experiment.winner
                )
            ),
            "total_runs": experiment.metrics_a.total_runs
            + experiment.metrics_b.total_runs,
            "created_at": experiment.created_at.isoformat(),
            "started_at": (
                experiment.started_at.isoformat() if experiment.started_at else None
            ),
            "ended_at": (
                experiment.ended_at.isoformat() if experiment.ended_at else None
            ),
        }


__all__ = ["ExperimentRouterService"]
