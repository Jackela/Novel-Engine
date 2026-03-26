"""World state and rumor propagation HTTP router."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.contexts.world.application.services.rumor_propagation_service import (
    RumorPropagationService,
)
from src.contexts.world.interface.http.error_handlers import (
    ResultErrorHandler,
)

router = APIRouter(prefix="/world", tags=["world"])


class RumorPropagationRequest(BaseModel):
    """Request model for rumor propagation."""

    world_id: UUID = Field(..., description="World ID to propagate rumors in")
    batch_size: int = Field(default=500, ge=1, le=10000, description="Batch size")


class RumorResponse(BaseModel):
    """Response model for a rumor."""

    id: str
    content: str
    truth_value: int
    origin_location_id: str
    spread_count: int
    is_dead: bool
    created_date: str


class RumorListResponse(BaseModel):
    """Response model for list of rumors."""

    world_id: str
    rumors: List[RumorResponse]
    total_count: int
    active_count: int


@router.post(
    "/rumors/propagate",
    response_model=Dict[str, Any],
    summary="Propagate rumors",
)
async def propagate_rumors(
    propagation: RumorPropagationRequest,
    service: RumorPropagationService = Depends(),
) -> dict[str, Any]:
    """Propagate rumors in the world."""
    from src.contexts.world.domain.aggregates.world_state import WorldState

    world = WorldState(id=str(propagation.world_id))

    if propagation.batch_size != 500:
        result = await service.propagate_rumors_batch(
            world, batch_size=propagation.batch_size
        )
    else:
        result = await service.propagate_rumors(world)

    rumors = ResultErrorHandler.handle(result, "propagate_rumors")

    return {
        "world_id": str(propagation.world_id),
        "propagated_count": len(rumors),
        "rumors": [
            {
                "id": str(r.rumor_id),
                "content": r.content,
                "truth_value": r.truth_value,
                "spread_count": r.spread_count,
            }
            for r in rumors
        ],
    }


@router.get(
    "/rumors/{world_id}",
    response_model=RumorListResponse,
    summary="Get active rumors",
)
async def get_active_rumors(
    world_id: UUID,
    service: RumorPropagationService = Depends(),
) -> RumorListResponse:
    """Get active rumors in world."""
    active_rumors = await service._rumor_repo.get_active_rumors(str(world_id))

    return RumorListResponse(
        world_id=str(world_id),
        rumors=[
            RumorResponse(
                id=str(r.rumor_id),
                content=r.content,
                truth_value=r.truth_value,
                origin_location_id=r.origin_location_id,
                spread_count=r.spread_count,
                is_dead=r.is_dead,
                created_date=str(r.created_date),
            )
            for r in active_rumors
        ],
        total_count=len(active_rumors),
        active_count=len([r for r in active_rumors if not r.is_dead]),
    )
