"""
In-Memory Experiment Repository Adapter

Warzone 4: AI Brain - BRAIN-018B
In-memory implementation of IExperimentRepository for development and testing.

Constitution Compliance:
- Article II (Hexagonal): Infrastructure adapter implementing port
- Article I (DDD): No business logic, only persistence
"""

from __future__ import annotations

import logging
from typing import Optional

from src.contexts.knowledge.application.ports.i_experiment_repository import (
    ExperimentRepositoryError,
    IExperimentRepository,
)
from src.contexts.knowledge.domain.models.prompt_experiment import (
    ExperimentStatus,
    PromptExperiment,
)

logger = logging.getLogger(__name__)


class InMemoryExperimentRepository(IExperimentRepository):
    """
    In-memory implementation of experiment repository.

    Why:
    - Provides fast persistence without external dependencies
    - Useful for development, testing, and single-instance deployments
    - Data is lost on restart (acceptable for draft experiments)

    Attributes:
        _experiments: Dictionary storing experiments by ID
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory repository."""
        self._experiments: dict[str, PromptExperiment] = {}

    async def save(self, experiment: PromptExperiment) -> str:
        """
        Persist an experiment (insert new or update existing).

        Args:
            experiment: PromptExperiment entity to persist

        Returns:
            The ID of the saved experiment

        Raises:
            ExperimentRepositoryError: If persistence operation fails
        """
        try:
            self._experiments[experiment.id] = experiment
            logger.debug(f"Saved experiment {experiment.id}: {experiment.name}")
            return experiment.id
        except Exception as e:
            raise ExperimentRepositoryError(f"Failed to save experiment: {e}") from e

    async def get_by_id(self, experiment_id: str) -> Optional[PromptExperiment]:
        """
        Retrieve an experiment by its unique identifier.

        Args:
            experiment_id: Unique identifier of the experiment

        Returns:
            PromptExperiment if found, None otherwise

        Raises:
            ExperimentRepositoryError: If retrieval operation fails
        """
        try:
            return self._experiments.get(experiment_id)
        except Exception as e:
            raise ExperimentRepositoryError(
                f"Failed to get experiment {experiment_id}: {e}"
            ) from e

    async def list_all(
        self,
        status: Optional[str] = None,
        prompt_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PromptExperiment]:
        """
        List all experiments with optional filtering.

        Args:
            status: Optional filter by status
            prompt_id: Optional filter by prompt ID
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of PromptExperiment entities

        Raises:
            ExperimentRepositoryError: If listing operation fails
        """
        try:
            experiments = list(self._experiments.values())

            # Filter by status
            if status:
                experiments = [e for e in experiments if e.status.value == status]

            # Filter by prompt ID (experiments where this prompt is either A or B)
            if prompt_id:
                experiments = [
                    e
                    for e in experiments
                    if e.prompt_a_id == prompt_id or e.prompt_b_id == prompt_id
                ]

            # Sort by created_at (newest first)
            experiments.sort(key=lambda e: e.created_at, reverse=True)

            # Apply pagination
            return experiments[offset : offset + limit]

        except Exception as e:
            raise ExperimentRepositoryError(f"Failed to list experiments: {e}") from e

    async def delete(self, experiment_id: str) -> bool:
        """
        Delete an experiment by its unique identifier.

        Args:
            experiment_id: Unique identifier of the experiment to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ExperimentRepositoryError: If deletion fails
        """
        try:
            if experiment_id in self._experiments:
                del self._experiments[experiment_id]
                logger.debug(f"Deleted experiment {experiment_id}")
                return True
            return False
        except Exception as e:
            raise ExperimentRepositoryError(
                f"Failed to delete experiment {experiment_id}: {e}"
            ) from e

    async def get_by_status(
        self, status: str, limit: int = 100
    ) -> list[PromptExperiment]:
        """
        List experiments by status.

        Args:
            status: Status to filter by
            limit: Maximum number of results

        Returns:
            List of PromptExperiment entities with the specified status

        Raises:
            ExperimentRepositoryError: If retrieval operation fails
        """
        try:
            experiments = [
                e for e in self._experiments.values() if e.status.value == status
            ]
            experiments.sort(key=lambda e: e.created_at, reverse=True)
            return experiments[:limit]
        except Exception as e:
            raise ExperimentRepositoryError(
                f"Failed to get experiments by status: {e}"
            ) from e

    async def get_active_for_prompt(self, prompt_id: str) -> list[PromptExperiment]:
        """
        Get active experiments for a specific prompt.

        Args:
            prompt_id: ID of the prompt template

        Returns:
            List of running or paused experiments that involve this prompt

        Raises:
            ExperimentRepositoryError: If retrieval operation fails
        """
        try:
            active_statuses = {ExperimentStatus.RUNNING, ExperimentStatus.PAUSED}
            return [
                e
                for e in self._experiments.values()
                if e.status in active_statuses
                and (e.prompt_a_id == prompt_id or e.prompt_b_id == prompt_id)
            ]
        except Exception as e:
            raise ExperimentRepositoryError(
                f"Failed to get active experiments: {e}"
            ) from e

    async def count(self) -> int:
        """
        Count total number of experiments.

        Returns:
            Total count of experiments

        Raises:
            ExperimentRepositoryError: If count operation fails
        """
        try:
            return len(self._experiments)
        except Exception as e:
            raise ExperimentRepositoryError(f"Failed to count experiments: {e}") from e


__all__ = ["InMemoryExperimentRepository"]
