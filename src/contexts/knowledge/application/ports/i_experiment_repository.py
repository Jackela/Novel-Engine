"""
IExperimentRepository Port Interface

Hexagonal architecture port defining the contract for prompt experiment persistence.

Warzone 4: AI Brain - BRAIN-018B

Constitution Compliance:
- Article II (Hexagonal): Domain/Application layer defines port, Infrastructure provides adapter
- Article I (DDD): Pure interface with no infrastructure coupling
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.models.prompt_experiment import PromptExperiment


class ExperimentRepositoryError(Exception):
    """Base exception for experiment repository errors."""

    pass


class ExperimentNotFoundError(ExperimentRepositoryError):
    """Raised when an experiment is not found."""

    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id
        super().__init__(f"Experiment with id '{experiment_id}' not found")


class IExperimentRepository(ABC):
    """
    Repository port for prompt experiment persistence.

    This interface defines the contract that infrastructure adapters must implement
    for persisting and retrieving PromptExperiment entities.

    Per Article II (Hexagonal Architecture):
    - Domain/Application layer defines this port
    - Infrastructure layer provides adapter implementation (SQLite, PostgreSQL, etc.)
    - Application use cases depend ONLY on this abstraction, never on concrete adapters

    Methods:
        save: Persist an experiment (create or update)
        get_by_id: Retrieve an experiment by its unique ID
        list_all: List all experiments with optional filtering
        delete: Remove an experiment
        get_by_status: List experiments by status
        get_active_for_prompt: Get active experiments for a specific prompt

    Constitution Compliance:
    - Article II (Hexagonal): Port interface in application layer
    - Article V (SOLID): ISP - Interface Segregation Principle (focused contract)
    - Article V (SOLID): DIP - Depend on abstractions, not concretions
    """

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
            prompt_id: Optional filter by prompt ID (experiments involving this prompt)
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of PromptExperiment entities

        Raises:
            ExperimentRepositoryError: If listing operation fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def get_active_for_prompt(
        self, prompt_id: str
    ) -> list[PromptExperiment]:
        """
        Get active experiments for a specific prompt.

        Args:
            prompt_id: ID of the prompt template

        Returns:
            List of running or paused experiments that involve this prompt

        Raises:
            ExperimentRepositoryError: If retrieval operation fails
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """
        Count total number of experiments.

        Returns:
            Total count of experiments

        Raises:
            ExperimentRepositoryError: If count operation fails
        """
        pass


__all__ = [
    "IExperimentRepository",
    "ExperimentRepositoryError",
    "ExperimentNotFoundError",
]
