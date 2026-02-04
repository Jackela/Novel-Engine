"""
Unit Tests for PromptExperiment Entity

Warzone 4: AI Brain - BRAIN-018A

Tests for A/B testing experiment functionality including:
- Experiment creation and validation
- Consistent hashing for variant assignment
- Metrics tracking (success_rate, user_rating, token_efficiency, latency)
- Experiment lifecycle (start, pause, resume, complete)
- Winner detection based on metrics
"""


import pytest

from src.contexts.knowledge.domain.models.prompt_experiment import (
    ExperimentMetric,
    ExperimentMetrics,
    ExperimentStatus,
    PromptExperiment,
)


class TestExperimentMetrics:
    """Tests for ExperimentMetrics value object."""

    def test_create_default_metrics(self) -> None:
        """Test creating metrics with default values."""
        metrics = ExperimentMetrics()
        assert metrics.total_runs == 0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
        assert metrics.total_tokens == 0
        assert metrics.total_latency_ms == 0.0
        assert metrics.rating_sum == 0.0
        assert metrics.rating_count == 0

    def test_metrics_success_rate(self) -> None:
        """Test success rate calculation."""
        metrics = ExperimentMetrics(
            total_runs=100,
            success_count=80,
            failure_count=20,
        )
        assert metrics.success_rate == 80.0

    def test_metrics_success_rate_zero_runs(self) -> None:
        """Test success rate with zero runs."""
        metrics = ExperimentMetrics()
        assert metrics.success_rate == 0.0

    def test_metrics_avg_rating(self) -> None:
        """Test average rating calculation."""
        metrics = ExperimentMetrics(
            rating_sum=20.0,
            rating_count=4,
        )
        assert metrics.avg_rating == 5.0

    def test_metrics_avg_rating_no_ratings(self) -> None:
        """Test average rating with no ratings."""
        metrics = ExperimentMetrics()
        assert metrics.avg_rating == 0.0

    def test_metrics_avg_tokens_per_run(self) -> None:
        """Test average tokens per run."""
        metrics = ExperimentMetrics(
            total_runs=10,
            success_count=8,
            failure_count=2,
            total_tokens=5000,
        )
        assert metrics.avg_tokens_per_run == 500.0

    def test_metrics_avg_latency_ms(self) -> None:
        """Test average latency calculation."""
        metrics = ExperimentMetrics(
            total_runs=5,
            success_count=3,
            failure_count=2,
            total_latency_ms=2500.0,
        )
        assert metrics.avg_latency_ms == 500.0

    def test_metrics_token_efficiency(self) -> None:
        """Test token efficiency calculation."""
        # 1000 tokens for 10 successes = 100 tokens per success
        metrics = ExperimentMetrics(
            total_runs=12,
            success_count=10,
            failure_count=2,
            total_tokens=1000,
        )
        assert metrics.token_efficiency == 100.0

    def test_metrics_token_efficiency_no_successes(self) -> None:
        """Test token efficiency with no successes returns infinity."""
        metrics = ExperimentMetrics(
            total_runs=5,
            success_count=0,
            failure_count=5,
            total_tokens=1000,
        )
        assert metrics.token_efficiency == float("inf")

    def test_record_run_success(self) -> None:
        """Test recording a successful run."""
        metrics = ExperimentMetrics()
        updated = metrics.record_run(success=True, tokens=100, latency_ms=50.0, rating=4.5)

        assert updated.total_runs == 1
        assert updated.success_count == 1
        assert updated.failure_count == 0
        assert updated.total_tokens == 100
        assert updated.total_latency_ms == 50.0
        assert updated.rating_sum == 4.5
        assert updated.rating_count == 1

    def test_record_run_failure(self) -> None:
        """Test recording a failed run."""
        metrics = ExperimentMetrics()
        updated = metrics.record_run(success=False, tokens=50, latency_ms=25.0)

        assert updated.total_runs == 1
        assert updated.success_count == 0
        assert updated.failure_count == 1
        assert updated.total_tokens == 50
        assert updated.total_latency_ms == 25.0

    def test_record_run_without_rating(self) -> None:
        """Test recording a run without rating."""
        metrics = ExperimentMetrics()
        updated = metrics.record_run(success=True)

        assert updated.rating_count == 0
        assert updated.rating_sum == 0.0

    def test_metrics_validation_negative_runs(self) -> None:
        """Test validation rejects negative total_runs."""
        with pytest.raises(ValueError, match="total_runs cannot be negative"):
            ExperimentMetrics(total_runs=-1)

    def test_metrics_validation_mismatched_counts(self) -> None:
        """Test validation rejects mismatched counts."""
        with pytest.raises(ValueError, match="must equal"):
            ExperimentMetrics(total_runs=10, success_count=5, failure_count=4)

    def test_metrics_to_dict(self) -> None:
        """Test metrics serialization to dict."""
        metrics = ExperimentMetrics(
            total_runs=100,
            success_count=80,
            failure_count=20,
            total_tokens=10000,
            total_latency_ms=5000.0,
            rating_sum=400.0,
            rating_count=100,
        )
        data = metrics.to_dict()

        assert data["total_runs"] == 100
        assert data["success_rate"] == 80.0
        assert data["avg_tokens_per_run"] == 100.0
        assert data["token_efficiency"] == 125.0
        assert data["avg_latency_ms"] == 50.0
        assert data["avg_rating"] == 4.0


class TestPromptExperimentCreation:
    """Tests for PromptExperiment creation and validation."""

    def test_create_experiment_with_factory(self) -> None:
        """Test creating an experiment via factory method."""
        experiment = PromptExperiment.create(
            name="Test Experiment",
            prompt_a_id="prompt-a",
            prompt_b_id="prompt-b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=50,
        )

        assert experiment.id
        assert experiment.name == "Test Experiment"
        assert experiment.prompt_a_id == "prompt-a"
        assert experiment.prompt_b_id == "prompt-b"
        assert experiment.metric == ExperimentMetric.SUCCESS_RATE
        assert experiment.traffic_split == 50
        assert experiment.status == ExperimentStatus.DRAFT

    def test_create_experiment_with_explicit_id(self) -> None:
        """Test creating an experiment with explicit ID."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            id="test-exp-123",
        )

        assert experiment.id == "test-exp-123"

    def test_experiment_validation_same_prompt_ids(self) -> None:
        """Test validation rejects same prompt_a_id and prompt_b_id."""
        with pytest.raises(ValueError, match="must be different"):
            PromptExperiment.create(
                name="Test",
                prompt_a_id="same-id",
                prompt_b_id="same-id",
                metric=ExperimentMetric.SUCCESS_RATE,
            )

    def test_experiment_validation_invalid_traffic_split(self) -> None:
        """Test validation rejects traffic_split outside 0-100."""
        with pytest.raises(ValueError, match="traffic_split must be between 0 and 100"):
            PromptExperiment.create(
                name="Test",
                prompt_a_id="a",
                prompt_b_id="b",
                metric=ExperimentMetric.SUCCESS_RATE,
                traffic_split=150,
            )

    def test_experiment_validation_invalid_min_sample_size(self) -> None:
        """Test validation rejects non-positive min_sample_size."""
        with pytest.raises(ValueError, match="min_sample_size must be positive"):
            PromptExperiment.create(
                name="Test",
                prompt_a_id="a",
                prompt_b_id="b",
                metric=ExperimentMetric.SUCCESS_RATE,
                min_sample_size=0,
            )

    def test_experiment_validation_invalid_confidence_threshold(self) -> None:
        """Test validation rejects confidence_threshold outside 0-1."""
        with pytest.raises(ValueError, match="confidence_threshold must be between 0 and 1"):
            PromptExperiment.create(
                name="Test",
                prompt_a_id="a",
                prompt_b_id="b",
                metric=ExperimentMetric.SUCCESS_RATE,
                confidence_threshold=1.5,
            )

    def test_experiment_empty_name(self) -> None:
        """Test validation rejects empty name."""
        with pytest.raises(ValueError, match="name cannot be empty"):
            PromptExperiment(
                id="test",
                name="",
                prompt_a_id="a",
                prompt_b_id="b",
                metric=ExperimentMetric.SUCCESS_RATE,
            )


class TestExperimentVariantAssignment:
    """Tests for consistent hashing variant assignment."""

    def test_assign_variant_deterministic(self) -> None:
        """Test that same user always gets same variant."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=50,
        )

        # Same user should always get same assignment
        variant1 = experiment.assign_variant("user-123")
        variant2 = experiment.assign_variant("user-123")
        _ = experiment.assign_variant("user-123", session_id="session-1")

        assert variant1 == variant2
        # Different session should still be consistent for same user
        assert variant1 in ("a", "b")

    def test_assign_variant_different_users(self) -> None:
        """Test that different users can get different variants."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=50,
        )

        # With enough users, both variants should be assigned
        assignments = set()
        for i in range(100):
            variant = experiment.assign_variant(f"user-{i}")
            assignments.add(variant)

        assert "a" in assignments
        assert "b" in assignments

    def test_assign_variant_with_session(self) -> None:
        """Test variant assignment with session ID."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=50,
        )

        # Same user + session should get same variant
        variant1 = experiment.assign_variant("user-123", "session-1")
        variant2 = experiment.assign_variant("user-123", "session-1")
        assert variant1 == variant2

        # Different session might get different variant
        variant3 = experiment.assign_variant("user-123", "session-2")
        # Either same or different is acceptable, but should be deterministic
        variant4 = experiment.assign_variant("user-123", "session-2")
        assert variant3 == variant4

    def test_assign_variant_distribution(self) -> None:
        """Test that traffic_split affects distribution."""
        # Create experiment with 30% to A, 70% to B
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=30,
        )

        # With large sample, distribution should approximate traffic_split
        a_count = 0
        b_count = 0
        for i in range(1000):
            variant = experiment.assign_variant(f"user-{i}")
            if variant == "a":
                a_count += 1
            else:
                b_count += 1

        # A should have roughly 30% (200-400 range is reasonable)
        assert 200 < a_count < 400
        assert 600 < b_count < 800

    def test_assign_variant_edge_cases(self) -> None:
        """Test edge cases for traffic split."""
        # 0% traffic to A means all to B
        experiment_all_b = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=0,
        )

        for i in range(100):
            assert experiment_all_b.assign_variant(f"user-{i}") == "b"

        # 100% traffic to A means all to A
        experiment_all_a = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            traffic_split=100,
        )

        for i in range(100):
            assert experiment_all_a.assign_variant(f"user-{i}") == "a"


class TestExperimentMetricsTracking:
    """Tests for recording experiment results."""

    def test_record_success_for_variant_a(self) -> None:
        """Test recording success for variant A."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        experiment.record_success("a", tokens=100, latency_ms=50.0, rating=5.0)

        assert experiment.metrics_a.total_runs == 1
        assert experiment.metrics_a.success_count == 1
        assert experiment.metrics_a.total_tokens == 100
        assert experiment.metrics_a.total_latency_ms == 50.0
        assert experiment.metrics_a.rating_sum == 5.0

        # Variant B should be unchanged
        assert experiment.metrics_b.total_runs == 0

    def test_record_success_for_variant_b(self) -> None:
        """Test recording success for variant B."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        experiment.record_success("b", tokens=200, latency_ms=75.0, rating=4.0)

        assert experiment.metrics_b.total_runs == 1
        assert experiment.metrics_b.success_count == 1
        assert experiment.metrics_a.total_runs == 0

    def test_record_failure_for_variant_a(self) -> None:
        """Test recording failure for variant A."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        experiment.record_failure("a", tokens=50, latency_ms=25.0)

        assert experiment.metrics_a.total_runs == 1
        assert experiment.metrics_a.failure_count == 1

    def test_record_with_invalid_variant_id(self) -> None:
        """Test that recording with invalid variant_id raises error."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        with pytest.raises(ValueError, match="must be prompt_a_id or prompt_b_id"):
            experiment.record_success("invalid-id")

        with pytest.raises(ValueError, match="must be prompt_a_id or prompt_b_id"):
            experiment.record_failure("invalid-id")

    def test_record_multiple_runs(self) -> None:
        """Test recording multiple runs accumulates metrics correctly."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        # Record several runs
        experiment.record_success("a", tokens=100, latency_ms=50.0, rating=5.0)
        experiment.record_success("a", tokens=150, latency_ms=75.0, rating=4.0)
        experiment.record_failure("a", tokens=50, latency_ms=25.0)
        experiment.record_success("b", tokens=120, latency_ms=60.0, rating=4.5)

        assert experiment.metrics_a.total_runs == 3
        assert experiment.metrics_a.success_count == 2
        assert experiment.metrics_a.failure_count == 1
        assert experiment.metrics_a.total_tokens == 300
        assert experiment.metrics_a.total_latency_ms == 150.0
        assert experiment.metrics_a.avg_rating == 4.5

        assert experiment.metrics_b.total_runs == 1
        assert experiment.metrics_b.success_count == 1


class TestExperimentLifecycle:
    """Tests for experiment state management."""

    def test_start_experiment(self) -> None:
        """Test starting a DRAFT experiment."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        assert experiment.status == ExperimentStatus.DRAFT
        assert experiment.started_at is None

        experiment.start()

        assert experiment.status == ExperimentStatus.RUNNING
        assert experiment.started_at is not None

    def test_start_non_draft_experiment_fails(self) -> None:
        """Test that starting a non-DRAFT experiment fails."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )
        experiment.start()

        with pytest.raises(ValueError, match="only DRAFT experiments can be started"):
            experiment.start()

    def test_pause_running_experiment(self) -> None:
        """Test pausing a RUNNING experiment."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )
        experiment.start()

        experiment.pause()

        assert experiment.status == ExperimentStatus.PAUSED

    def test_pause_non_running_experiment_fails(self) -> None:
        """Test that pausing a non-RUNNING experiment fails."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        with pytest.raises(ValueError, match="only RUNNING experiments can be paused"):
            experiment.pause()

    def test_resume_paused_experiment(self) -> None:
        """Test resuming a PAUSED experiment."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )
        experiment.start()
        experiment.pause()

        experiment.resume()

        assert experiment.status == ExperimentStatus.RUNNING

    def test_resume_non_paused_experiment_fails(self) -> None:
        """Test that resuming a non-PAUSED experiment fails."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )

        with pytest.raises(ValueError, match="only PAUSED experiments can be resumed"):
            experiment.resume()

    def test_complete_experiment(self) -> None:
        """Test completing an experiment."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=10,
        )
        experiment.start()

        # Add some data
        for _ in range(10):
            experiment.record_success("a", tokens=100, latency_ms=50.0, rating=5.0)
            experiment.record_failure("b")

        experiment.complete("a")

        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.winner == "a"
        assert experiment.ended_at is not None

    def test_complete_experiment_auto_detect_winner(self) -> None:
        """Test auto-detecting winner on completion."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=10,
        )
        experiment.start()

        # A has 100% success, B has 50%
        for _ in range(10):
            experiment.record_success("a", tokens=100, latency_ms=50.0)
        for _ in range(5):
            experiment.record_success("b", tokens=100, latency_ms=50.0)
        for _ in range(5):
            experiment.record_failure("b")

        experiment.complete()  # No winner specified

        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.winner == "a"

    def test_complete_experiment_insufficient_data(self) -> None:
        """Test completing with insufficient data returns no winner."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=100,
        )
        experiment.start()

        # Not enough samples
        for _ in range(10):
            experiment.record_success("a")
            experiment.record_success("b")

        experiment.complete()

        assert experiment.status == ExperimentStatus.COMPLETED
        assert experiment.winner is None  # No winner due to insufficient data

    def test_complete_experiment_invalid_winner(self) -> None:
        """Test that completing with invalid winner_id fails."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )
        experiment.start()

        with pytest.raises(ValueError, match="must be prompt_a_id or prompt_b_id"):
            experiment.complete("invalid-id")


class TestExperimentWinnerDetection:
    """Tests for winner detection logic."""

    def test_detect_winner_by_success_rate(self) -> None:
        """Test winner detection based on success rate."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=10,
        )

        # A: 80% success rate, B: 60% success rate
        for _ in range(8):
            experiment.record_success("a")
        for _ in range(2):
            experiment.record_failure("a")
        for _ in range(6):
            experiment.record_success("b")
        for _ in range(4):
            experiment.record_failure("b")

        winner = experiment._detect_winner()
        assert winner == "a"

    def test_detect_winner_by_user_rating(self) -> None:
        """Test winner detection based on user rating."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.USER_RATING,
            min_sample_size=10,
        )

        # A: 4.5 avg rating, B: 3.5 avg rating
        for _ in range(10):
            experiment.record_success("a", rating=4.5)
        for _ in range(10):
            experiment.record_success("b", rating=3.5)

        winner = experiment._detect_winner()
        assert winner == "a"

    def test_detect_winner_by_token_efficiency(self) -> None:
        """Test winner detection based on token efficiency."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.TOKEN_EFFICIENCY,
            min_sample_size=10,
        )

        # A: 100 tokens per success, B: 150 tokens per success
        for _ in range(10):
            experiment.record_success("a", tokens=100)
        for _ in range(10):
            experiment.record_success("b", tokens=150)

        winner = experiment._detect_winner()
        assert winner == "a"  # Lower token efficiency wins

    def test_detect_winner_by_latency(self) -> None:
        """Test winner detection based on latency."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.LATENCY,
            min_sample_size=10,
        )

        # A: 50ms avg, B: 100ms avg
        for _ in range(10):
            experiment.record_success("a", latency_ms=50.0)
        for _ in range(10):
            experiment.record_success("b", latency_ms=100.0)

        winner = experiment._detect_winner()
        assert winner == "a"  # Lower latency wins

    def test_detect_winner_no_successes(self) -> None:
        """Test winner detection when one variant has no successes."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.TOKEN_EFFICIENCY,
            min_sample_size=10,
        )

        # A: all failures, B: some successes
        for _ in range(10):
            experiment.record_failure("a")
        for _ in range(10):
            experiment.record_success("b", tokens=100)

        winner = experiment._detect_winner()
        assert winner == "b"

    def test_detect_winner_tie(self) -> None:
        """Test winner detection with tied metrics."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=10,
        )

        # Same success rate for both
        for _ in range(10):
            experiment.record_success("a")
        for _ in range(10):
            experiment.record_success("b")

        winner = experiment._detect_winner()
        assert winner is None  # Tie


class TestExperimentSerialization:
    """Tests for experiment serialization."""

    def test_to_dict(self) -> None:
        """Test serializing experiment to dictionary."""
        experiment = PromptExperiment.create(
            name="Test Experiment",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            description="Testing something",
            traffic_split=60,
            created_by="user-123",
        )

        data = experiment.to_dict()

        assert data["id"] == experiment.id
        assert data["name"] == "Test Experiment"
        assert data["description"] == "Testing something"
        assert data["prompt_a_id"] == "a"
        assert data["prompt_b_id"] == "b"
        assert data["metric"] == "success_rate"
        assert data["traffic_split"] == 60
        assert data["status"] == "draft"
        assert data["created_by"] == "user-123"

    def test_from_dict(self) -> None:
        """Test deserializing experiment from dictionary."""
        data = {
            "id": "test-123",
            "name": "Test Experiment",
            "description": "Testing",
            "prompt_a_id": "a",
            "prompt_b_id": "b",
            "metric": "success_rate",
            "traffic_split": 50,
            "status": "running",
            "metrics_a": {
                "total_runs": 10,
                "success_count": 8,
                "failure_count": 2,
                "total_tokens": 1000,
                "total_latency_ms": 500.0,
                "rating_sum": 40.0,
                "rating_count": 10,
            },
            "metrics_b": {
                "total_runs": 10,
                "success_count": 6,
                "failure_count": 4,
                "total_tokens": 1200,
                "total_latency_ms": 600.0,
                "rating_sum": 30.0,
                "rating_count": 10,
            },
            "winner": None,
            "created_at": "2025-02-04T00:00:00+00:00",
            "started_at": "2025-02-04T01:00:00+00:00",
            "ended_at": None,
            "created_by": "user-123",
            "min_sample_size": 100,
            "confidence_threshold": 0.95,
        }

        experiment = PromptExperiment.from_dict(data)

        assert experiment.id == "test-123"
        assert experiment.name == "Test Experiment"
        assert experiment.status == ExperimentStatus.RUNNING
        assert experiment.metrics_a.total_runs == 10
        assert experiment.metrics_a.success_count == 8

    def test_round_trip_serialization(self) -> None:
        """Test that to_dict and from_dict are inverses."""
        original = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
        )
        original.start()
        original.record_success("a", tokens=100, latency_ms=50.0, rating=5.0)
        original.record_failure("b")

        data = original.to_dict()
        restored = PromptExperiment.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.status == original.status
        assert restored.metrics_a.total_runs == original.metrics_a.total_runs
        assert restored.metrics_a.success_count == original.metrics_a.success_count


class TestExperimentResults:
    """Tests for experiment results summary."""

    def test_get_results(self) -> None:
        """Test getting experiment results summary."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=10,
        )
        experiment.start()

        # Add some data
        for _ in range(10):
            experiment.record_success("a", tokens=100, latency_ms=50.0, rating=5.0)
        for _ in range(5):
            experiment.record_success("b", tokens=120, latency_ms=60.0, rating=4.0)
        for _ in range(5):
            experiment.record_failure("b")

        results = experiment.get_results()

        assert results["experiment_id"] == experiment.id
        assert results["name"] == "Test"
        assert results["status"] == "running"
        assert results["metric"] == "success_rate"
        assert results["winner"] is None  # Still running

        # Check variant data
        assert results["variant_a"]["prompt_id"] == "a"
        assert results["variant_a"]["total_runs"] == 10
        assert results["variant_a"]["success_rate"] == 100.0

        assert results["variant_b"]["prompt_id"] == "b"
        assert results["variant_b"]["total_runs"] == 10
        assert results["variant_b"]["success_rate"] == 50.0

        # Check comparison
        assert results["comparison"]["success_rate_diff"] == 50.0

    def test_get_results_with_winner(self) -> None:
        """Test getting results after completion."""
        experiment = PromptExperiment.create(
            name="Test",
            prompt_a_id="a",
            prompt_b_id="b",
            metric=ExperimentMetric.SUCCESS_RATE,
            min_sample_size=10,
        )
        experiment.start()

        # A wins
        for _ in range(10):
            experiment.record_success("a", tokens=100, latency_ms=50.0)
        for _ in range(5):
            experiment.record_success("b", tokens=100, latency_ms=50.0)
        for _ in range(5):
            experiment.record_failure("b")

        experiment.complete("a")

        results = experiment.get_results()

        assert results["status"] == "completed"
        assert results["winner"] == "A"
