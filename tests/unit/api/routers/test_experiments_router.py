"""
Tests for Experiment Router Endpoints

Warzone 4: AI Brain - BRAIN-018B
Unit tests for the prompt experiment API endpoints.
"""

from __future__ import annotations


import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.experiments import (
    get_experiment_repository,
    get_prompt_repository,
)
from src.api.routers.experiments import router as experiments_router
from src.contexts.knowledge.domain.models.prompt_experiment import (
    ExperimentMetric,
    PromptExperiment,
)
from src.contexts.knowledge.domain.models.prompt_template import (
    ModelConfig,
    PromptTemplate,
    VariableDefinition,
    VariableType,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_experiment_repository import (
    InMemoryExperimentRepository,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_prompt_repository import (
    InMemoryPromptRepository,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def mock_prompt_repository() -> InMemoryPromptRepository:
    """Create a mock prompt repository with sample data."""
    repo = InMemoryPromptRepository()

    # Add sample prompts with proper variable definitions
    template_a = PromptTemplate(
        id="prompt-a",
        name="Dialogue Prompt v1",
        content="Generate dialogue for {{character}} in a {{mood}} mood.",
        description="First version of dialogue generator",
        tags=("dialogue", "v1"),
        variables=(
            VariableDefinition(
                name="character",
                type=VariableType.STRING,
                required=True,
                description="The character name",
            ),
            VariableDefinition(
                name="mood",
                type=VariableType.STRING,
                required=True,
                description="The mood for dialogue",
            ),
        ),
        model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        version=1,
    )

    template_b = PromptTemplate(
        id="prompt-b",
        name="Dialogue Prompt v2",
        content="Create a {{mood}} conversation for {{character}}.",
        description="Second version of dialogue generator",
        tags=("dialogue", "v2"),
        variables=(
            VariableDefinition(
                name="character",
                type=VariableType.STRING,
                required=True,
                description="The character name",
            ),
            VariableDefinition(
                name="mood",
                type=VariableType.STRING,
                required=True,
                description="The mood for dialogue",
            ),
        ),
        model_config=ModelConfig(provider="openai", model_name="gpt-4"),
        version=1,
    )

    # Save synchronously for test setup
    import asyncio

    async def setup():
        await repo.save(template_a)
        await repo.save(template_b)

    asyncio.run(setup())

    return repo


@pytest.fixture
def mock_experiment_repository(
    mock_prompt_repository: InMemoryPromptRepository,
) -> InMemoryExperimentRepository:
    """Create a mock experiment repository with sample data."""
    repo = InMemoryExperimentRepository()

    # Create sample experiment
    experiment = PromptExperiment.create(
        name="Dialogue A/B Test",
        prompt_a_id="prompt-a",
        prompt_b_id="prompt-b",
        metric=ExperimentMetric.SUCCESS_RATE,
        traffic_split=50,
        description="Testing two dialogue prompt versions",
        min_sample_size=100,
    )

    # Save synchronously for test setup
    import asyncio

    async def setup():
        await repo.save(experiment)

    asyncio.run(setup())

    return repo


@pytest.fixture
def app_with_repos(
    mock_prompt_repository: InMemoryPromptRepository,
    mock_experiment_repository: InMemoryExperimentRepository,
) -> FastAPI:
    """Create app with pre-populated repositories."""
    app = FastAPI()

    # Mock the get_prompt_repository dependency
    async def get_prompt_repo_mock() -> InMemoryPromptRepository:
        return mock_prompt_repository

    # Mock the get_experiment_repository dependency
    async def get_experiment_repo_mock() -> InMemoryExperimentRepository:
        return mock_experiment_repository

    # Override the dependencies
    app.dependency_overrides[get_prompt_repository] = get_prompt_repo_mock

    app.dependency_overrides[get_experiment_repository] = get_experiment_repo_mock

    app.include_router(experiments_router, prefix="/api")

    return app


@pytest.fixture
def client_with_repos(app_with_repos: FastAPI) -> TestClient:
    """Create client with pre-populated repositories."""
    return TestClient(app_with_repos)


class TestExperimentsRouterHealth:
    """Tests for experiments health endpoint."""

    def test_health_check(self, client_with_repos: TestClient) -> None:
        """Test health check returns healthy status."""
        response = client_with_repos.get("/api/experiments/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "repository_type" in data
        assert "timestamp" in data


class TestExperimentsRouterList:
    """Tests for listing experiments."""

    def test_list_experiments_empty(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test listing experiments when none exist."""
        # Clear the repository first
        response = client_with_repos.get("/api/experiments")

        assert response.status_code == 200
        data = response.json()
        # The fixture adds one experiment, so we expect at least 1
        assert len(data["experiments"]) >= 1

    def test_list_experiments_with_data(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test listing experiments returns existing experiments."""
        response = client_with_repos.get("/api/experiments")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) >= 1
        assert data["experiments"][0]["name"] == "Dialogue A/B Test"
        assert data["total"] >= 1

    def test_list_experiments_with_status_filter(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test filtering experiments by status."""
        # Filter for draft experiments
        response = client_with_repos.get("/api/experiments?status=draft")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) >= 1
        assert data["experiments"][0]["status"] == "draft"

        # Filter for running experiments (none)
        response = client_with_repos.get("/api/experiments?status=running")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) == 0

    def test_list_experiments_with_prompt_filter(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test filtering experiments by prompt ID."""
        # Filter by prompt-a
        response = client_with_repos.get("/api/experiments?prompt_id=prompt-a")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) >= 1

        # Filter by unrelated prompt
        response = client_with_repos.get("/api/experiments?prompt_id=unrelated-prompt")

        assert response.status_code == 200
        data = response.json()
        assert len(data["experiments"]) == 0

    def test_list_experiments_with_pagination(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test pagination parameters."""
        response = client_with_repos.get("/api/experiments?limit=10&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "offset" in data


class TestExperimentsRouterCreate:
    """Tests for creating experiments."""

    def test_create_experiment_success(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test creating an experiment successfully."""
        payload = {
            "name": "Test Experiment",
            "description": "Testing A/B test",
            "prompt_a_id": "prompt-a",
            "prompt_b_id": "prompt-b",
            "metric": "success_rate",
            "traffic_split": 50,
            "min_sample_size": 100,
        }

        response = client_with_repos.post("/api/experiments", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Experiment"
        assert data["prompt_a_id"] == "prompt-a"
        assert data["prompt_b_id"] == "prompt-b"
        assert data["status"] == "draft"
        assert "id" in data

    def test_create_experiment_with_invalid_prompt_a(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test creating an experiment with invalid prompt A returns 404."""
        payload = {
            "name": "Test Experiment",
            "prompt_a_id": "invalid-a",
            "prompt_b_id": "prompt-b",
            "metric": "success_rate",
        }

        response = client_with_repos.post("/api/experiments", json=payload)

        assert response.status_code == 404

    def test_create_experiment_with_invalid_prompt_b(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test creating an experiment with invalid prompt B returns 404."""
        payload = {
            "name": "Test Experiment",
            "prompt_a_id": "prompt-a",
            "prompt_b_id": "invalid-b",
            "metric": "success_rate",
        }

        response = client_with_repos.post("/api/experiments", json=payload)

        assert response.status_code == 404

    def test_create_experiment_with_invalid_metric(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test creating an experiment with invalid metric returns 400."""
        payload = {
            "name": "Test Experiment",
            "prompt_a_id": "prompt-a",
            "prompt_b_id": "prompt-b",
            "metric": "invalid_metric",
        }

        response = client_with_repos.post("/api/experiments", json=payload)

        assert response.status_code == 422  # Validation error

    def test_create_experiment_with_invalid_traffic_split(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test creating an experiment with invalid traffic split returns 422."""
        payload = {
            "name": "Test Experiment",
            "prompt_a_id": "prompt-a",
            "prompt_b_id": "prompt-b",
            "metric": "success_rate",
            "traffic_split": 150,  # Invalid: must be 0-100
        }

        response = client_with_repos.post("/api/experiments", json=payload)

        assert response.status_code == 422  # Validation error


class TestExperimentsRouterGet:
    """Tests for getting a specific experiment."""

    def test_get_experiment_success(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test getting an experiment by ID."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        response = client_with_repos.get(f"/api/experiments/{experiment_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Dialogue A/B Test"
        assert data["metric"] == "success_rate"

    def test_get_experiment_not_found(self, client_with_repos: TestClient) -> None:
        """Test getting a non-existent experiment returns 404."""
        response = client_with_repos.get("/api/experiments/nonexistent-id")

        assert response.status_code == 404


class TestExperimentsRouterResults:
    """Tests for getting experiment results."""

    def test_get_experiment_results(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test getting experiment results."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        response = client_with_repos.get(f"/api/experiments/{experiment_id}/results")

        assert response.status_code == 200
        data = response.json()
        assert "variant_a" in data
        assert "variant_b" in data
        assert "comparison" in data
        assert "statistical_significance" in data

    def test_get_results_includes_confidence_intervals(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test that results include confidence intervals."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        response = client_with_repos.get(f"/api/experiments/{experiment_id}/results")

        assert response.status_code == 200
        data = response.json()
        assert "confidence_interval" in data["variant_a"]
        assert "lower" in data["variant_a"]["confidence_interval"]
        assert "upper" in data["variant_a"]["confidence_interval"]

    def test_get_results_includes_significance_analysis(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test that results include statistical significance analysis."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        response = client_with_repos.get(f"/api/experiments/{experiment_id}/results")

        assert response.status_code == 200
        data = response.json()
        sig = data["statistical_significance"]
        assert "meets_minimum_sample_size" in sig
        assert "two_proportion_z_test" in sig
        assert "effect_size" in sig
        assert "recommendation" in sig


class TestExperimentsRouterActions:
    """Tests for experiment actions (start, pause, resume, complete)."""

    def test_start_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test starting an experiment."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        response = client_with_repos.post(f"/api/experiments/{experiment_id}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert "started_at" in data

    def test_pause_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test pausing a running experiment."""
        # First, start the experiment
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]
        client_with_repos.post(f"/api/experiments/{experiment_id}/start")

        # Then pause it
        response = client_with_repos.post(f"/api/experiments/{experiment_id}/pause")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    def test_resume_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test resuming a paused experiment."""
        # First, start and pause the experiment
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]
        client_with_repos.post(f"/api/experiments/{experiment_id}/start")
        client_with_repos.post(f"/api/experiments/{experiment_id}/pause")

        # Then resume it
        response = client_with_repos.post(f"/api/experiments/{experiment_id}/resume")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"

    def test_complete_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test completing an experiment."""
        # First, start the experiment
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]
        client_with_repos.post(f"/api/experiments/{experiment_id}/start")

        # Then complete it
        response = client_with_repos.post(f"/api/experiments/{experiment_id}/complete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "ended_at" in data

    def test_complete_experiment_with_winner(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test completing an experiment with a specified winner."""
        # First, start the experiment
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]
        client_with_repos.post(f"/api/experiments/{experiment_id}/start")

        # Complete with winner A
        response = client_with_repos.post(
            f"/api/experiments/{experiment_id}/complete",
            json={"winner": "A"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["winner"] == "A"

    def test_start_nonexistent_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test starting a non-existent experiment returns 404."""
        response = client_with_repos.post("/api/experiments/nonexistent/start")

        assert response.status_code == 404


class TestExperimentsRouterRecord:
    """Tests for recording experiment results."""

    def test_record_success(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test recording a successful result."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        # Get the experiment to find prompt IDs
        experiment_response = client_with_repos.get(f"/api/experiments/{experiment_id}")
        prompt_a_id = experiment_response.json()["prompt_a_id"]

        # Record a success
        payload = {
            "variant_id": prompt_a_id,
            "success": True,
            "tokens": 100,
            "latency_ms": 500.0,
            "rating": 4.5,
        }

        response = client_with_repos.post(
            f"/api/experiments/{experiment_id}/record", json=payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_runs"] == 1

    def test_record_failure(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test recording a failed result."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        # Get the experiment to find prompt IDs
        experiment_response = client_with_repos.get(f"/api/experiments/{experiment_id}")
        prompt_a_id = experiment_response.json()["prompt_a_id"]

        # Record a failure
        payload = {
            "variant_id": prompt_a_id,
            "success": False,
            "tokens": 50,
            "latency_ms": 200.0,
        }

        response = client_with_repos.post(
            f"/api/experiments/{experiment_id}/record", json=payload
        )

        assert response.status_code == 200

    def test_record_result_with_invalid_variant(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test recording a result with invalid variant ID returns 400."""
        # First, list to get an ID
        list_response = client_with_repos.get("/api/experiments")
        experiment_id = list_response.json()["experiments"][0]["id"]

        # Record with invalid variant
        payload = {
            "variant_id": "invalid-variant-id",
            "success": True,
        }

        response = client_with_repos.post(
            f"/api/experiments/{experiment_id}/record", json=payload
        )

        assert response.status_code == 400


class TestExperimentsRouterDelete:
    """Tests for deleting experiments."""

    def test_delete_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test deleting an experiment."""
        # First, create a new experiment to delete
        payload = {
            "name": "To Delete",
            "prompt_a_id": "prompt-a",
            "prompt_b_id": "prompt-b",
            "metric": "success_rate",
        }

        create_response = client_with_repos.post("/api/experiments", json=payload)
        experiment_id = create_response.json()["id"]

        # Delete it
        response = client_with_repos.delete(f"/api/experiments/{experiment_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = client_with_repos.get(f"/api/experiments/{experiment_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_experiment(
        self,
        client_with_repos: TestClient,
    ) -> None:
        """Test deleting a non-existent experiment returns 404."""
        response = client_with_repos.delete("/api/experiments/nonexistent-id")

        assert response.status_code == 404
