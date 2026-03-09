"""Experiment and Prompt API schemas for the Novel Engine.

This module contains schemas for prompt management and A/B testing including:
- Prompt Management schemas (BRAIN-015)
- Prompt Analytics schemas (BRAIN-022B)
- Prompt Experiment schemas (BRAIN-018B)

Created as part of PREP-002 (Operation Vanguard).
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, JsonValue, field_validator

# === Prompt Management Schemas (BRAIN-015) ===


class PromptVariableDefinition(BaseModel):
    """Schema for a prompt variable definition."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Variable name (must match {{var}} in template)",
    )
    type: str = Field(
        ..., description="Variable type: string, integer, float, boolean, list, dict"
    )
    default_value: Optional[JsonValue] = Field(
        None, description="Default value if not provided"
    )
    description: str = Field(
        default="", max_length=500, description="Human-readable description"
    )
    required: bool = Field(
        default=True, description="Whether this variable must be provided"
    )


class PromptVariableValue(BaseModel):
    """Schema for a prompt variable value during rendering."""

    name: str = Field(..., min_length=1, description="Variable name")
    value: JsonValue = Field(..., description="Variable value")


class PromptSummary(BaseModel):
    """Schema for a prompt template summary (list view)."""

    id: str = Field(..., description="Prompt template UUID")
    name: str = Field(..., description="Prompt name")
    description: str = Field(default="", description="Prompt description")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    version: int = Field(default=1, description="Version number")
    model_provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name")
    variable_count: int = Field(default=0, description="Number of variables")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class PromptModelConfig(BaseModel):
    """Schema for prompt model configuration."""

    provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=1000, ge=1, description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        default=1.0, ge=0.0, le=1.0, description="Nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        default=0.0, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=0.0, ge=-2.0, le=2.0, description="Presence penalty"
    )


class PromptDetailResponse(BaseModel):
    """Schema for a full prompt template detail."""

    id: str = Field(..., description="Prompt template UUID")
    name: str = Field(..., description="Prompt name")
    description: str = Field(default="", description="Prompt description")
    content: str = Field(
        ..., description="Template content with {{variable}} placeholders"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    extends: List[str] = Field(
        default_factory=list,
        description="Parent template IDs/names this template extends",
    )
    version: int = Field(default=1, description="Version number")
    parent_version_id: Optional[str] = Field(None, description="Parent version ID")
    llm_config: PromptModelConfig = Field(
        ..., description="Model configuration", alias="model_config"
    )
    variables: List[PromptVariableDefinition] = Field(
        default_factory=list, description="Variable definitions"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")

    model_config = {"populate_by_name": True}


class PromptListResponse(BaseModel):
    """Response model for listing prompts."""

    prompts: List[PromptSummary] = Field(
        default_factory=list, description="List of prompt summaries"
    )
    total: int = Field(default=0, description="Total count of prompts")
    limit: int = Field(default=100, description="Page size limit")
    offset: int = Field(default=0, description="Pagination offset")


class PromptCreateRequest(BaseModel):
    """Request model for creating a new prompt template."""

    name: str = Field(..., min_length=1, max_length=200, description="Prompt name")
    content: str = Field(
        ..., min_length=1, description="Template content with {{variable}} placeholders"
    )
    description: str = Field(
        default="", max_length=1000, description="Prompt description"
    )
    tags: List[str] = Field(
        default_factory=list, max_length=20, description="Tags for categorization"
    )
    extends: List[str] = Field(
        default_factory=list,
        max_length=10,
        description="Parent template IDs/names to extend",
    )
    variables: List[PromptVariableDefinition] = Field(
        default_factory=list, description="Variable definitions"
    )
    model_provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-4", description="Model name")
    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        default=None, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=None, ge=-2.0, le=2.0, description="Presence penalty"
    )


class PromptUpdateRequest(BaseModel):
    """Request model for updating a prompt template (creates new version)."""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=200, description="Prompt name"
    )
    content: Optional[str] = Field(
        default=None, min_length=1, description="Template content"
    )
    description: Optional[str] = Field(
        default=None, max_length=1000, description="Prompt description"
    )
    tags: Optional[List[str]] = Field(
        default=None, max_length=20, description="Tags for categorization"
    )
    extends: Optional[List[str]] = Field(
        default=None, max_length=10, description="Parent template IDs/names to extend"
    )
    variables: Optional[List[PromptVariableDefinition]] = Field(
        default=None, description="Variable definitions"
    )
    model_provider: Optional[str] = Field(default=None, description="LLM provider")
    model_name: Optional[str] = Field(default=None, description="Model name")
    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        default=None, ge=-2.0, le=2.0, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=None, ge=-2.0, le=2.0, description="Presence penalty"
    )


class PromptRenderRequest(BaseModel):
    """Request model for rendering a prompt template."""

    variables: List[PromptVariableValue] = Field(
        default_factory=list, description="Variable values for rendering"
    )
    strict: bool = Field(
        default=True, description="Raise errors for missing required variables"
    )


class PromptRenderResponse(BaseModel):
    """Response model for a rendered prompt."""

    rendered: str = Field(..., description="Rendered prompt content")
    variables_used: List[str] = Field(
        default_factory=list, description="Variable names that were used"
    )
    variables_missing: List[str] = Field(
        default_factory=list, description="Required variables that were missing"
    )
    template_id: str = Field(..., description="Template ID that was rendered")
    template_name: str = Field(..., description="Template name")
    token_count: Optional[int] = Field(None, description="Estimated token count")
    llm_config: Optional[Dict[str, Any]] = Field(
        None, description="Model configuration used", alias="model_config"
    )

    model_config = {"populate_by_name": True}


class PromptGenerateRequest(BaseModel):
    """Request model for generating output using a prompt template.

    BRAIN-020B: Frontend: Prompt Playground - Integration
    Combines rendering and LLM generation in a single request.
    """

    variables: List[PromptVariableValue] = Field(
        default_factory=list, description="Variable values for rendering the prompt"
    )
    # Override model config from the prompt template
    provider: Optional[str] = Field(
        None, description="Override LLM provider (uses prompt config if not specified)"
    )
    model_name: Optional[str] = Field(
        None, description="Override model name (uses prompt config if not specified)"
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Override sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, description="Override max tokens to generate"
    )
    top_p: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Override nucleus sampling"
    )
    frequency_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Override frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        None, ge=-2.0, le=2.0, description="Override presence penalty"
    )
    strict: bool = Field(
        default=True, description="Raise errors for missing required variables"
    )


class PromptGenerateResponse(BaseModel):
    """Response model for prompt generation output.

    BRAIN-020B: Frontend: Prompt Playground - Integration
    Contains both the rendered prompt and the LLM-generated output.
    """

    rendered: str = Field(..., description="The rendered prompt content")
    output: str = Field(..., description="The LLM-generated output")
    template_id: str = Field(..., description="Template ID that was used")
    template_name: str = Field(..., description="Template name")
    prompt_tokens: int = Field(..., description="Estimated input token count")
    output_tokens: Optional[int] = Field(
        None, description="Output token count if available"
    )
    total_tokens: int = Field(..., description="Total token count")
    latency_ms: float = Field(..., description="Generation time in milliseconds")
    model_used: str = Field(..., description="Model that was used for generation")
    error: Optional[str] = Field(None, description="Error message if generation failed")


# === Prompt Analytics Schemas (BRAIN-022B) ===


class PromptAnalyticsTimePeriod(str, Enum):
    """Time period for analytics aggregation."""

    day = "day"
    week = "week"
    month = "month"
    all = "all"


class PromptTimeSeriesDataPoint(BaseModel):
    """Single data point in time series analytics."""

    period: str = Field(
        ..., description="Time period identifier (ISO date or week number)"
    )
    total_uses: int = Field(default=0, ge=0, description="Total uses in this period")
    successful_uses: int = Field(
        default=0, ge=0, description="Successful uses in this period"
    )
    failed_uses: int = Field(default=0, ge=0, description="Failed uses in this period")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_latency_ms: float = Field(default=0.0, ge=0, description="Average latency")
    avg_rating: float = Field(default=0.0, ge=0, le=5, description="Average rating")


class PromptRatingDistribution(BaseModel):
    """Distribution of user ratings."""

    one_star: int = Field(default=0, ge=0, description="Count of 1-star ratings")
    two_star: int = Field(default=0, ge=0, description="Count of 2-star ratings")
    three_star: int = Field(default=0, ge=0, description="Count of 3-star ratings")
    four_star: int = Field(default=0, ge=0, description="Count of 4-star ratings")
    five_star: int = Field(default=0, ge=0, description="Count of 5-star ratings")


class PromptAnalyticsResponse(BaseModel):
    """Response model for prompt analytics.

    BRAIN-022B: Backend: Prompt Analytics - API
    Provides usage statistics and metrics over time.
    """

    prompt_id: str = Field(..., description="Prompt template ID")
    prompt_name: str = Field(..., description="Prompt name")
    period: PromptAnalyticsTimePeriod = Field(
        default=PromptAnalyticsTimePeriod.all, description="Time period for aggregation"
    )

    # Overall metrics
    total_uses: int = Field(default=0, ge=0, description="Total number of uses")
    successful_uses: int = Field(default=0, ge=0, description="Successful generations")
    failed_uses: int = Field(default=0, ge=0, description="Failed generations")
    success_rate: float = Field(
        default=0.0, ge=0, le=100, description="Success rate percentage"
    )

    # Token metrics
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    total_input_tokens: int = Field(default=0, ge=0, description="Total input tokens")
    total_output_tokens: int = Field(default=0, ge=0, description="Total output tokens")
    avg_tokens_per_use: float = Field(
        default=0.0, ge=0, description="Average tokens per use"
    )
    avg_input_tokens: float = Field(
        default=0.0, ge=0, description="Average input tokens"
    )
    avg_output_tokens: float = Field(
        default=0.0, ge=0, description="Average output tokens"
    )

    # Latency metrics
    total_latency_ms: float = Field(default=0.0, ge=0, description="Total latency")
    avg_latency_ms: float = Field(
        default=0.0, ge=0, description="Average latency in ms"
    )
    min_latency_ms: float = Field(default=0.0, ge=0, description="Minimum latency")
    max_latency_ms: float = Field(default=0.0, ge=0, description="Maximum latency")

    # Rating metrics
    rating_sum: float = Field(default=0.0, description="Sum of ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    avg_rating: float = Field(default=0.0, ge=0, le=5, description="Average rating")
    rating_distribution: PromptRatingDistribution = Field(
        default_factory=PromptRatingDistribution, description="Distribution of ratings"
    )

    # Time series data
    time_series: List[PromptTimeSeriesDataPoint] = Field(
        default_factory=list, description="Usage over time grouped by period"
    )

    # Metadata
    first_used: Optional[str] = Field(None, description="First use timestamp")
    last_used: Optional[str] = Field(None, description="Last use timestamp")
    generated_at: str = Field(..., description="When analytics were generated")


class PromptAnalyticsRequest(BaseModel):
    """Request parameters for analytics query."""

    period: PromptAnalyticsTimePeriod = Field(
        default=PromptAnalyticsTimePeriod.all,
        description="Time period for aggregation (day, week, month, all)",
    )
    start_date: Optional[str] = Field(
        None, description="ISO 8601 start date for filtering (exclusive of period)"
    )
    end_date: Optional[str] = Field(
        None, description="ISO 8601 end date for filtering (exclusive of period)"
    )
    workspace_id: Optional[str] = Field(None, description="Filter by workspace ID")
    limit: int = Field(
        default=100, ge=1, le=1000, description="Maximum time series data points"
    )


# === Prompt Experiment Schemas (BRAIN-018B) ===


class ExperimentMetricsResponse(BaseModel):
    """Schema for experiment metrics."""

    total_runs: int = Field(default=0, ge=0, description="Total number of runs")
    success_count: int = Field(default=0, ge=0, description="Number of successful runs")
    failure_count: int = Field(default=0, ge=0, description="Number of failed runs")
    success_rate: float = Field(
        default=0.0, ge=0, le=100, description="Success rate percentage"
    )
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_tokens_per_run: float = Field(
        default=0.0, ge=0, description="Average tokens per run"
    )
    token_efficiency: float = Field(
        default=0.0, ge=0, description="Tokens per successful generation"
    )
    total_latency_ms: float = Field(
        default=0.0, ge=0, description="Total latency in milliseconds"
    )
    avg_latency_ms: float = Field(
        default=0.0, ge=0, description="Average latency in milliseconds"
    )
    rating_sum: float = Field(default=0.0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    avg_rating: float = Field(
        default=0.0, ge=0, le=5, description="Average user rating"
    )


class ConfidenceIntervalResponse(BaseModel):
    """Schema for confidence interval of a metric."""

    lower: float = Field(
        ..., ge=0, le=100, description="Lower bound of confidence interval"
    )
    upper: float = Field(
        ..., ge=0, le=100, description="Upper bound of confidence interval"
    )


class ExperimentVariantResponse(BaseModel):
    """Schema for an experiment variant with metrics."""

    prompt_id: str = Field(..., description="Prompt template ID")
    total_runs: int = Field(default=0, ge=0, description="Total number of runs")
    success_count: int = Field(default=0, ge=0, description="Number of successful runs")
    failure_count: int = Field(default=0, ge=0, description="Number of failed runs")
    success_rate: float = Field(
        default=0.0, ge=0, le=100, description="Success rate percentage"
    )
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")
    avg_tokens_per_run: float = Field(
        default=0.0, ge=0, description="Average tokens per run"
    )
    token_efficiency: float = Field(
        default=0.0, ge=0, description="Tokens per successful generation"
    )
    total_latency_ms: float = Field(
        default=0.0, ge=0, description="Total latency in milliseconds"
    )
    avg_latency_ms: float = Field(
        default=0.0, ge=0, description="Average latency in milliseconds"
    )
    rating_sum: float = Field(default=0.0, description="Sum of all ratings")
    rating_count: int = Field(default=0, ge=0, description="Number of ratings")
    avg_rating: float = Field(
        default=0.0, ge=0, le=5, description="Average user rating"
    )
    confidence_interval: Optional[ConfidenceIntervalResponse] = Field(
        default=None, description="Confidence interval for success rate"
    )


class ExperimentComparisonResponse(BaseModel):
    """Schema for variant comparison."""

    success_rate_diff: float = Field(
        default=0.0, description="Difference in success rate (A - B)"
    )
    success_rate_rel_diff: float = Field(
        default=0.0, description="Relative difference in success rate (%)"
    )
    avg_rating_diff: float = Field(
        default=0.0, description="Difference in average rating (A - B)"
    )
    avg_rating_rel_diff: float = Field(
        default=0.0, description="Relative difference in rating (%)"
    )
    token_efficiency_diff: float = Field(
        default=0.0, description="Difference in token efficiency (A - B)"
    )
    avg_latency_diff: float = Field(
        default=0.0, description="Difference in latency (A - B)"
    )
    avg_latency_rel_diff: float = Field(
        default=0.0, description="Relative difference in latency (%)"
    )


class ExperimentTimelineResponse(BaseModel):
    """Schema for experiment timeline."""

    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    started_at: Optional[str] = Field(None, description="ISO 8601 start timestamp")
    ended_at: Optional[str] = Field(None, description="ISO 8601 end timestamp")


class ExperimentResultsResponse(BaseModel):
    """Schema for experiment results."""

    experiment_id: str = Field(..., description="Experiment ID")
    name: str = Field(..., description="Experiment name")
    status: str = Field(..., description="Experiment status")
    metric: str = Field(..., description="Primary metric for comparison")
    winner: Optional[str] = Field(None, description="Winning variant (A or B)")
    min_sample_size: int = Field(default=100, ge=1, description="Minimum sample size")
    traffic_split: Dict[str, int] = Field(
        default_factory=dict, description="Traffic split percentage"
    )
    variant_a: ExperimentVariantResponse = Field(..., description="Variant A metrics")
    variant_b: ExperimentVariantResponse = Field(..., description="Variant B metrics")
    comparison: ExperimentComparisonResponse = Field(
        ..., description="Variant comparison"
    )
    timeline: ExperimentTimelineResponse = Field(..., description="Experiment timeline")
    statistical_significance: Optional[Dict[str, Any]] = Field(
        None, description="Statistical significance analysis"
    )


class ExperimentSummaryResponse(BaseModel):
    """Schema for experiment summary (list view)."""

    id: str = Field(..., description="Experiment ID")
    name: str = Field(..., description="Experiment name")
    description: str = Field(default="", description="Experiment description")
    status: str = Field(..., description="Experiment status")
    metric: str = Field(..., description="Primary metric for comparison")
    prompt_a_id: str = Field(..., description="Variant A prompt ID")
    prompt_b_id: str = Field(..., description="Variant B prompt ID")
    traffic_split: int = Field(default=50, description="Traffic split for variant A")
    winner: Optional[str] = Field(None, description="Winning variant (A or B)")
    total_runs: int = Field(
        default=0, ge=0, description="Total runs across both variants"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    started_at: Optional[str] = Field(None, description="ISO 8601 start timestamp")
    ended_at: Optional[str] = Field(None, description="ISO 8601 end timestamp")


class ExperimentListResponse(BaseModel):
    """Response model for listing experiments."""

    experiments: List[ExperimentSummaryResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of experiments")
    limit: int = Field(default=100, description="Page size limit")
    offset: int = Field(default=0, description="Pagination offset")


class ExperimentCreateRequest(BaseModel):
    """Request model for creating an experiment."""

    name: str = Field(..., min_length=1, max_length=200, description="Experiment name")
    description: str = Field(
        default="", max_length=1000, description="Experiment description"
    )
    prompt_a_id: str = Field(..., description="Variant A prompt template ID")
    prompt_b_id: str = Field(..., description="Variant B prompt template ID")
    metric: str = Field(
        ...,
        description="Primary metric: success_rate, user_rating, token_efficiency, latency",
    )
    traffic_split: int = Field(
        default=50, ge=0, le=100, description="Traffic split for variant A (0-100)"
    )
    min_sample_size: int = Field(
        default=100, ge=10, description="Minimum sample size per variant"
    )
    confidence_threshold: float = Field(
        default=0.95, ge=0.5, le=0.99, description="Confidence threshold"
    )

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: str) -> str:
        valid_metrics = {"success_rate", "user_rating", "token_efficiency", "latency"}
        if v not in valid_metrics:
            raise ValueError(f"Metric must be one of: {valid_metrics}")
        return v


class ExperimentUpdateRequest(BaseModel):
    """Request model for updating an experiment."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    status: Optional[str] = Field(
        default=None, description="New status: draft, running, paused, completed"
    )
    min_sample_size: Optional[int] = Field(default=None, ge=10)

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        valid_statuses = {"draft", "running", "paused", "completed", "archived"}
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v


class ExperimentRecordRequest(BaseModel):
    """Request model for recording a run result."""

    variant_id: str = Field(
        ..., description="The variant that was used (prompt_a_id or prompt_b_id)"
    )
    success: bool = Field(..., description="Whether the generation was successful")
    tokens: int = Field(default=0, ge=0, description="Number of tokens consumed")
    latency_ms: float = Field(
        default=0.0, ge=0, description="Response time in milliseconds"
    )
    rating: Optional[float] = Field(
        None, ge=1.0, le=5.0, description="User rating (1-5)"
    )


class ExperimentActionRequest(BaseModel):
    """Request model for experiment actions (start, pause, resume, complete)."""

    winner: Optional[str] = Field(
        None, description="Winning variant (for complete action)"
    )
