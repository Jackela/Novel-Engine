"""Knowledge and Brain API schemas for the Novel Engine.

This module contains schemas for the AI Brain / RAG system including:
- Routing Configuration schemas (BRAIN-028B)
- Brain Settings schemas (BRAIN-033)
- RAG Context schemas (BRAIN-036-02)
- Knowledge Metadata schemas (OPT-006)
- Async Ingestion Job schemas (OPT-005)

Created as part of PREP-002 (Operation Vanguard).
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# === Routing Configuration Schemas ===
# BRAIN-028B: Model Routing Configuration


class TaskRoutingRuleSchema(BaseModel):
    """Routing rule for a specific task type."""

    task_type: str = Field(..., description="Task type: creative, logical, fast, cheap")
    provider: str = Field(
        ..., description="LLM provider: openai, anthropic, gemini, ollama, mock"
    )
    model_name: str = Field("", description="Model name (empty for provider default)")
    temperature: Optional[float] = Field(
        None, ge=0, le=2, description="Temperature override"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=1000000, description="Max tokens override"
    )
    priority: int = Field(
        0, ge=0, description="Rule priority (higher = more important)"
    )
    enabled: bool = Field(True, description="Whether this rule is active")


class RoutingConstraintsSchema(BaseModel):
    """Constraints for model routing decisions."""

    max_cost_per_1m_tokens: Optional[float] = Field(
        None, ge=0, description="Maximum cost per 1M tokens (USD)"
    )
    max_latency_ms: Optional[int] = Field(
        None, ge=0, description="Maximum acceptable latency (ms)"
    )
    preferred_providers: List[str] = Field(
        default_factory=list, description="Provider preference order"
    )
    blocked_providers: List[str] = Field(
        default_factory=list, description="Providers to never use"
    )
    require_capabilities: List[str] = Field(
        default_factory=list, description="Required capabilities"
    )


class CircuitBreakerRuleSchema(BaseModel):
    """Circuit breaker configuration for a specific model."""

    model_key: str = Field(..., description="Model identifier (provider:model)")
    failure_threshold: int = Field(
        5, ge=1, le=100, description="Failures before opening circuit"
    )
    timeout_seconds: int = Field(
        60, ge=1, le=3600, description="Seconds before half-open state"
    )
    enabled: bool = Field(True, description="Whether circuit breaker is enabled")


class RoutingConfigResponse(BaseModel):
    """Response model for routing configuration."""

    workspace_id: str = Field(
        ..., description="Workspace identifier (empty for global)"
    )
    scope: str = Field(..., description="Configuration scope: global or workspace")
    task_rules: List[TaskRoutingRuleSchema] = Field(
        default_factory=list, description="Task routing rules"
    )
    constraints: Optional[RoutingConstraintsSchema] = Field(
        None, description="Routing constraints"
    )
    circuit_breaker_rules: List[CircuitBreakerRuleSchema] = Field(
        default_factory=list, description="Circuit breaker rules"
    )
    enable_circuit_breaker: bool = Field(
        True, description="Whether circuit breaker is enabled"
    )
    enable_fallback: bool = Field(True, description="Whether fallback chain is enabled")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 update timestamp")
    version: int = Field(..., ge=1, description="Configuration version")


class RoutingConfigUpdateRequest(BaseModel):
    """Request model for updating routing configuration."""

    task_rules: Optional[List[TaskRoutingRuleSchema]] = Field(
        None, description="New task rules"
    )
    constraints: Optional[RoutingConstraintsSchema] = Field(
        None, description="New constraints"
    )
    circuit_breaker_rules: Optional[List[CircuitBreakerRuleSchema]] = Field(
        None, description="New circuit breaker rules"
    )
    enable_circuit_breaker: Optional[bool] = Field(
        None, description="Circuit breaker setting"
    )
    enable_fallback: Optional[bool] = Field(None, description="Fallback setting")


class RoutingConfigResetRequest(BaseModel):
    """Request model for resetting routing configuration."""

    workspace_id: str = Field(
        ..., description="Workspace identifier (empty for global)"
    )


class RoutingStatsResponse(BaseModel):
    """Response model for routing statistics."""

    total_decisions: int = Field(..., ge=0, description="Total routing decisions made")
    fallback_count: int = Field(
        ..., ge=0, description="Number of times fallback was used"
    )
    fallback_rate: float = Field(
        ..., ge=0, le=1, description="Rate of fallback usage (0-1)"
    )
    reason_counts: Dict[str, int] = Field(
        default_factory=dict, description="Count by routing reason"
    )
    provider_counts: Dict[str, int] = Field(
        default_factory=dict, description="Count by provider"
    )
    avg_routing_time_ms: float = Field(
        ..., ge=0, description="Average routing decision time"
    )
    open_circuits: List[Dict[str, Any]] = Field(
        default_factory=list, description="Currently open circuits"
    )
    total_circuits: int = Field(..., ge=0, description="Total circuit breakers tracked")


# === Brain Settings Schemas ===
# BRAIN-033: Frontend Brain Settings


class APIKeysRequest(BaseModel):
    """Request model for updating API keys."""

    openai_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_key: Optional[str] = Field(None, description="Anthropic API key")
    gemini_key: Optional[str] = Field(None, description="Google Gemini API key")
    ollama_base_url: Optional[str] = Field(None, description="Ollama base URL")


class APIKeysResponse(BaseModel):
    """Response model for API keys (values masked)."""

    openai_key: str = Field(..., description="Masked OpenAI API key")
    anthropic_key: str = Field(..., description="Masked Anthropic API key")
    gemini_key: str = Field(..., description="Masked Gemini API key")
    ollama_base_url: Optional[str] = Field(None, description="Ollama base URL")
    has_openai: bool = Field(default=False, description="Whether OpenAI key is set")
    has_anthropic: bool = Field(
        default=False, description="Whether Anthropic key is set"
    )
    has_gemini: bool = Field(default=False, description="Whether Gemini key is set")


class RAGConfigRequest(BaseModel):
    """Request model for updating RAG configuration."""

    enabled: Optional[bool] = Field(None, description="Whether RAG is enabled")
    max_chunks: Optional[int] = Field(
        None, ge=1, le=50, description="Maximum chunks to retrieve"
    )
    score_threshold: Optional[float] = Field(
        None, ge=0, le=1, description="Minimum relevance score"
    )
    context_token_limit: Optional[int] = Field(
        None, ge=100, le=100000, description="Max tokens for context"
    )
    include_sources: Optional[bool] = Field(
        None, description="Whether to include source citations"
    )
    chunk_size: Optional[int] = Field(
        None, ge=100, le=10000, description="Default chunk size for ingestion"
    )
    chunk_overlap: Optional[int] = Field(
        None, ge=0, le=1000, description="Chunk overlap for ingestion"
    )
    hybrid_search_weight: Optional[float] = Field(
        None, ge=0, le=1, description="Vector search weight (1-BM25 weight)"
    )


class RAGConfigResponse(BaseModel):
    """Response model for RAG configuration."""

    enabled: bool = Field(..., description="Whether RAG is enabled")
    max_chunks: int = Field(..., description="Maximum chunks to retrieve")
    score_threshold: float = Field(..., description="Minimum relevance score")
    context_token_limit: int = Field(..., description="Max tokens for context")
    include_sources: bool = Field(
        ..., description="Whether to include source citations"
    )
    chunk_size: int = Field(..., description="Default chunk size for ingestion")
    chunk_overlap: int = Field(..., description="Chunk overlap for ingestion")
    hybrid_search_weight: float = Field(
        ..., description="Vector search weight (1-BM25 weight)"
    )


class KnowledgeBaseStatusResponse(BaseModel):
    """Response model for knowledge base status."""

    total_entries: int = Field(..., ge=0, description="Total entries in knowledge base")
    characters_count: int = Field(..., ge=0, description="Number of character entries")
    lore_count: int = Field(..., ge=0, description="Number of lore entries")
    scenes_count: int = Field(..., ge=0, description="Number of scene entries")
    plotlines_count: int = Field(..., ge=0, description="Number of plotline entries")
    last_sync: Optional[str] = Field(
        None, description="ISO 8601 timestamp of last sync"
    )
    is_healthy: bool = Field(..., description="Whether the vector store is healthy")


class BrainSettingsResponse(BaseModel):
    """Combined response for all brain settings."""

    api_keys: APIKeysResponse
    rag_config: RAGConfigResponse
    knowledge_base: KnowledgeBaseStatusResponse


# BRAIN-036-02: Context Inspector Schemas


class RetrievedChunkResponse(BaseModel):
    """A retrieved chunk from the knowledge base."""

    chunk_id: str = Field(..., description="ID of the chunk")
    source_id: str = Field(..., description="ID of the source entity")
    source_type: str = Field(
        ..., description="Type of source (CHARACTER, LORE, SCENE, etc.)"
    )
    content: str = Field(..., description="Chunk content text")
    score: float = Field(..., ge=0, le=1, description="Relevance score (0-1)")
    token_count: int = Field(..., ge=0, description="Estimated token count")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    used: bool = Field(
        default=False,
        description="Whether this chunk was used in the generated response (BRAIN-036-03)",
    )


class RAGContextResponse(BaseModel):
    """Response model for RAG context retrieval."""

    query: str = Field(..., description="The query used for retrieval")
    chunks: List[RetrievedChunkResponse] = Field(..., description="Retrieved chunks")
    total_tokens: int = Field(
        ..., ge=0, description="Total tokens in retrieved context"
    )
    chunk_count: int = Field(..., ge=0, description="Number of chunks retrieved")
    sources: List[str] = Field(default_factory=list, description="Source references")


# === Knowledge Metadata Schemas ===
# OPT-006: Structured Metadata Schema


class ConfidentialityLevel(str, Enum):
    """Confidentiality levels for knowledge entries."""

    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


class KnowledgeMetadataSchema(BaseModel):
    """Structured metadata for knowledge entries (OPT-006)."""

    world_version: str = Field(
        "1.0.0", description="Version of the world this knowledge belongs to"
    )
    confidentiality_level: ConfidentialityLevel = Field(
        default=ConfidentialityLevel.PUBLIC, description="Access control classification"
    )
    last_accessed: Optional[str] = Field(
        None, description="ISO 8601 timestamp of last access (UTC)"
    )
    source_version: int = Field(
        1, ge=1, description="Version of the source content for tracking updates"
    )

    @field_validator("last_accessed", mode="before")
    @classmethod
    def validate_last_accessed(cls, v: Optional[str]) -> Optional[str]:
        """Validate last_accessed is a valid ISO 8601 timestamp if provided."""
        if v is not None:
            try:
                # Parse and re-format to ensure valid ISO format
                from datetime import datetime

                parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
                return parsed.isoformat()
            except ValueError:
                raise ValueError("last_accessed must be a valid ISO 8601 timestamp")
        return v


# === Async Ingestion Job Schemas ===
# OPT-005: Async Ingestion Job API


class IngestionJobStatus(str, Enum):
    """Status of an async ingestion job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StartIngestionJobRequest(BaseModel):
    """Request model for starting an async ingestion job."""

    content: str = Field(..., description="Text content to ingest")
    source_type: str = Field(
        ..., description="Type of source (CHARACTER, LORE, SCENE, etc.)"
    )
    source_id: str = Field(..., description="Unique ID of the source entity")
    tags: Optional[List[str]] = Field(None, description="Optional tags for filtering")
    extra_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional additional metadata (preserved for backward compatibility)",
    )
    # OPT-006: Structured metadata fields
    world_version: Optional[str] = Field(
        None, description="World version (default: 1.0.0)"
    )
    confidentiality_level: Optional[ConfidentialityLevel] = Field(
        None, description="Access control level (default: PUBLIC)"
    )


class IngestionJobResponse(BaseModel):
    """Response model for ingestion job status."""

    job_id: str = Field(..., description="Unique identifier for the job")
    status: IngestionJobStatus = Field(..., description="Current job status")
    progress: float = Field(
        ..., ge=0, le=100, description="Progress percentage (0-100)"
    )
    source_id: str = Field(..., description="ID of the source being ingested")
    source_type: str = Field(..., description="Type of source")
    created_at: str = Field(..., description="ISO 8601 timestamp when job was created")
    started_at: Optional[str] = Field(
        None, description="ISO 8601 timestamp when job started"
    )
    completed_at: Optional[str] = Field(
        None, description="ISO 8601 timestamp when job completed"
    )
    error: Optional[str] = Field(None, description="Error message if job failed")
    chunk_count: Optional[int] = Field(
        None, description="Number of chunks created (when complete)"
    )
    entries_created: Optional[int] = Field(
        None, description="Number of entries created (when complete)"
    )


class StartIngestionJobResponse(BaseModel):
    """Response model for starting an ingestion job."""

    job_id: str = Field(..., description="Unique identifier for the job")
    status: IngestionJobStatus = Field(..., description="Initial job status")
    message: str = Field(..., description="Status message")
