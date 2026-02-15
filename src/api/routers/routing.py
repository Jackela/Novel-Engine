"""
Model Routing Configuration API Router

Warzone 4: AI Brain - BRAIN-028B
REST API for managing model routing configuration.

Constitution Compliance:
- Article II (Hexagonal): Router handles HTTP, Service handles business logic
- Article I (DDD): No business logic in router layer
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from src.api.schemas import (
    CircuitBreakerRuleSchema,
    RoutingConfigResetRequest,
    RoutingConfigResponse,
    RoutingConfigUpdateRequest,
    RoutingConstraintsSchema,
    RoutingStatsResponse,
    TaskRoutingRuleSchema,
)
from src.contexts.knowledge.application.ports.i_routing_config_repository import (
    RoutingConfigNotFoundError,
    RoutingConfigRepositoryError,
)
from src.contexts.knowledge.application.services.model_registry import ModelRegistry
from src.contexts.knowledge.application.services.model_router import ModelRouter
from src.contexts.knowledge.domain.models.routing_config import (
    CircuitBreakerRule,
    LLMProvider,
    RoutingConstraints,
    TaskRoutingRule,
    TaskType,
    WorkspaceRoutingConfig,
)
from src.contexts.knowledge.infrastructure.adapters.in_memory_routing_config_repository import (
    InMemoryRoutingConfigRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["routing"])


def get_routing_repository(request: Request) -> InMemoryRoutingConfigRepository:
    """
    Get or create the routing configuration repository from app state.

    Why: Lazy initialization and singleton pattern for the repository.

    Args:
        request: FastAPI request object

    Returns:
        The routing configuration repository instance
    """
    repository = getattr(request.app.state, "routing_config_repository", None)
    if repository is None:
        repository = InMemoryRoutingConfigRepository()
        request.app.state.routing_config_repository = repository
        logger.info("Initialized InMemoryRoutingConfigRepository")
    return repository


def get_model_router(
    request: Request,
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> ModelRouter:
    """
    Get the model router with routing configuration support.

    Why: Dependency injection for testability.

    Args:
        request: FastAPI request object
        repository: The routing configuration repository

    Returns:
        ModelRouter instance
    """
    router = getattr(request.app.state, "model_router", None)
    if router is None:
        # Get or create model registry
        registry = getattr(request.app.state, "model_registry", None)
        if registry is None:
            registry = ModelRegistry()
            request.app.state.model_registry = registry

        router = ModelRouter(registry)
        request.app.state.model_router = router

    return router


def _parse_task_rule(schema: TaskRoutingRuleSchema) -> TaskRoutingRule:
    """Parse API schema to domain TaskRoutingRule."""
    return TaskRoutingRule(
        task_type=TaskType(schema.task_type),
        provider=LLMProvider(schema.provider),
        model_name=schema.model_name,
        temperature=schema.temperature,
        max_tokens=schema.max_tokens,
        priority=schema.priority,
        enabled=schema.enabled,
    )


def _parse_constraints(
    schema: Optional[RoutingConstraintsSchema],
) -> Optional[RoutingConstraints]:
    """Parse API schema to domain RoutingConstraints."""
    if schema is None:
        return None

    return RoutingConstraints(
        max_cost_per_1m_tokens=schema.max_cost_per_1m_tokens,
        max_latency_ms=schema.max_latency_ms,
        preferred_providers=tuple(LLMProvider(p) for p in schema.preferred_providers),
        blocked_providers=tuple(LLMProvider(p) for p in schema.blocked_providers),
        require_capabilities=tuple(schema.require_capabilities),
    )


def _parse_circuit_breaker_rule(schema: CircuitBreakerRuleSchema) -> CircuitBreakerRule:
    """Parse API schema to domain CircuitBreakerRule."""
    return CircuitBreakerRule(
        model_key=schema.model_key,
        failure_threshold=schema.failure_threshold,
        timeout_seconds=schema.timeout_seconds,
        enabled=schema.enabled,
    )


def _domain_to_response(config: WorkspaceRoutingConfig) -> RoutingConfigResponse:
    """Convert domain config to API response."""
    return RoutingConfigResponse(
        workspace_id=config.workspace_id or "global",
        scope=config.scope.value,
        task_rules=[
            TaskRoutingRuleSchema(
                task_type=rule.task_type.value,
                provider=rule.provider.value,
                model_name=rule.model_name,
                temperature=rule.temperature,
                max_tokens=rule.max_tokens,
                priority=rule.priority,
                enabled=rule.enabled,
            )
            for rule in config.task_rules
        ],
        constraints=(
            RoutingConstraintsSchema(
                max_cost_per_1m_tokens=config.constraints.max_cost_per_1m_tokens,
                max_latency_ms=config.constraints.max_latency_ms,
                preferred_providers=[
                    p.value for p in config.constraints.preferred_providers
                ],
                blocked_providers=[
                    p.value for p in config.constraints.blocked_providers
                ],
                require_capabilities=list(config.constraints.require_capabilities),
            )
            if config.constraints
            else None
        ),
        circuit_breaker_rules=[
            CircuitBreakerRuleSchema(
                model_key=rule.model_key,
                failure_threshold=rule.failure_threshold,
                timeout_seconds=rule.timeout_seconds,
                enabled=rule.enabled,
            )
            for rule in config.circuit_breaker_rules
        ],
        enable_circuit_breaker=config.enable_circuit_breaker,
        enable_fallback=config.enable_fallback,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
        version=config.version,
    )


# ==================== Query Endpoints ====================


@router.get("/routing/config", response_model=RoutingConfigResponse)
async def get_routing_config(
    workspace_id: Optional[str] = None,
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> RoutingConfigResponse:
    """
    Get routing configuration for a workspace.

    Query Parameters:
        workspace_id: Workspace identifier (defaults to global if not provided)

    Returns:
        Routing configuration for the workspace (or global if workspace not configured)

    Raises:
        404: If global config not found
        500: If retrieval fails
    """
    try:
        workspace = workspace_id or ""
        config = await repository.get_config(workspace, fallback_to_global=True)
        return _domain_to_response(config)

    except RoutingConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RoutingConfigRepositoryError as e:
        logger.error(f"Failed to get routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/routing/config/global", response_model=RoutingConfigResponse)
async def get_global_routing_config(
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> RoutingConfigResponse:
    """
    Get the global routing configuration.

    Returns:
        Global routing configuration

    Raises:
        404: If global config not found
        500: If retrieval fails
    """
    try:
        config = await repository.get_global_config()
        return _domain_to_response(config)

    except RoutingConfigNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RoutingConfigRepositoryError as e:
        logger.error(f"Failed to get global routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/routing/config/list", response_model=list[RoutingConfigResponse])
async def list_routing_configs(
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> list[RoutingConfigResponse]:
    """
    List all workspace routing configurations.

    Returns:
        List of all workspace configurations (excluding global)

    Raises:
        500: If listing fails
    """
    try:
        configs = await repository.list_configs()
        return [_domain_to_response(c) for c in configs]

    except RoutingConfigRepositoryError as e:
        logger.error(f"Failed to list routing configs: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/routing/stats", response_model=RoutingStatsResponse)
async def get_routing_stats(
    router: ModelRouter = Depends(get_model_router),
) -> RoutingStatsResponse:
    """
    Get routing statistics and analytics.

    Returns:
        Routing statistics including fallback rate, provider usage, circuit breaker state

    Raises:
        500: If stats retrieval fails
    """
    try:
        stats = router.get_routing_stats()
        return RoutingStatsResponse(
            total_decisions=stats["total_decisions"],
            fallback_count=stats["fallback_count"],
            fallback_rate=stats.get("fallback_rate", 0.0),
            reason_counts=stats.get("reason_counts", {}),
            provider_counts=stats.get("provider_counts", {}),
            avg_routing_time_ms=stats.get("avg_routing_time_ms", 0.0),
            open_circuits=stats.get("open_circuits", []),
            total_circuits=stats.get("total_circuits", 0),
        )

    except Exception as e:
        logger.error(f"Failed to get routing stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== Mutation Endpoints ====================


@router.put("/routing/config", response_model=RoutingConfigResponse)
async def update_routing_config(
    payload: RoutingConfigUpdateRequest,
    workspace_id: Optional[str] = None,
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> RoutingConfigResponse:
    """
    Update routing configuration for a workspace.

    Creates a new version of the configuration with the specified changes.
    Unchanged fields retain their current values.

    Query Parameters:
        workspace_id: Workspace identifier (defaults to global if not provided)

    Request Body:
        Partial configuration with fields to update

    Returns:
        Updated routing configuration

    Raises:
        400: If validation fails
        404: If config not found
        500: If update fails
    """
    try:
        workspace = workspace_id or ""

        # Get existing config
        try:
            existing = await repository.get_config(workspace, fallback_to_global=False)
        except RoutingConfigNotFoundError:
            # Create new config if it doesn't exist
            if workspace == "":
                existing = WorkspaceRoutingConfig.create_global()
            else:
                existing = WorkspaceRoutingConfig.create_workspace(workspace)

        # Parse updates
        task_rules = None
        if payload.task_rules is not None:
            task_rules = tuple(_parse_task_rule(r) for r in payload.task_rules)

        constraints = None
        if payload.constraints is not None:
            constraints = _parse_constraints(payload.constraints)

        circuit_breaker_rules = None
        if payload.circuit_breaker_rules is not None:
            circuit_breaker_rules = tuple(
                _parse_circuit_breaker_rule(r) for r in payload.circuit_breaker_rules
            )

        # Create updated config
        updated = existing.create_updated(
            task_rules=task_rules,
            constraints=constraints,
            circuit_breaker_rules=circuit_breaker_rules,
            enable_circuit_breaker=payload.enable_circuit_breaker,
            enable_fallback=payload.enable_fallback,
        )

        # Save
        await repository.save_config(updated)

        return _domain_to_response(updated)

    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RoutingConfigRepositoryError as e:
        logger.error(f"Failed to update routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/routing/config/reset", response_model=RoutingConfigResponse)
async def reset_routing_config(
    payload: RoutingConfigResetRequest,
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> RoutingConfigResponse:
    """
    Reset routing configuration to defaults.

    Request Body:
        workspace_id: Workspace identifier (empty string for global)

    Returns:
        New default configuration

    Raises:
        500: If reset fails
    """
    try:
        workspace = payload.workspace_id
        config = await repository.reset_to_defaults(workspace)
        return _domain_to_response(config)

    except RoutingConfigRepositoryError as e:
        logger.error(f"Failed to reset routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/routing/config", status_code=204, response_class=Response)
async def delete_routing_config(
    workspace_id: str,
    repository: InMemoryRoutingConfigRepository = Depends(get_routing_repository),
) -> Response:
    """
    Delete routing configuration for a workspace.

    Query Parameters:
        workspace_id: Workspace identifier to delete

    Returns:
        204 No Content on success

    Raises:
        500: If delete fails
    """
    try:
        deleted = await repository.delete_config(workspace_id)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Configuration for workspace '{workspace_id}' not found",
            )

        return Response(status_code=204)

    except HTTPException:
        raise
    except RoutingConfigRepositoryError as e:
        logger.error(f"Failed to delete routing config: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/routing/circuit-breaker/{model_key}/reset", response_model=dict[str, str]
)
async def reset_circuit_breaker(
    model_key: str,
    router: ModelRouter = Depends(get_model_router),
) -> dict[str, str]:
    """
    Reset a circuit breaker to closed state.

    Path Parameters:
        model_key: Model identifier (provider:model)

    Returns:
        Success message

    Raises:
        404: If circuit breaker not found
        500: If reset fails
    """
    try:
        success = router.reset_circuit_breaker(model_key)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Circuit breaker for '{model_key}' not found"
            )

        return {"status": "reset", "model_key": model_key}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset circuit breaker: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/routing/circuit-breaker/{model_key}", response_model=dict[str, Any])
async def get_circuit_breaker_state(
    model_key: str,
    router: ModelRouter = Depends(get_model_router),
) -> dict[str, Any]:
    """
    Get circuit breaker state for a specific model.

    Path Parameters:
        model_key: Model identifier (provider:model)

    Returns:
        Circuit breaker state info

    Raises:
        404: If circuit breaker not found
        500: If retrieval fails
    """
    try:
        state = router.get_circuit_breaker_state(model_key)
        if state is None:
            raise HTTPException(
                status_code=404, detail=f"Circuit breaker for '{model_key}' not found"
            )

        return state

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get circuit breaker state: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


__all__ = ["router"]
