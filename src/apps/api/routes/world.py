"""Canonical world rumor routes with stable public paths."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/world", tags=["world"])

_rumor_store: dict[str, list["RumorState"]] = {}


@dataclass(slots=True)
class RumorState:
    """Minimal canonical rumor record."""

    rumor_id: str
    content: str
    truth_value: int
    origin_location_id: str
    spread_count: int
    is_dead: bool
    created_date: str

    def to_dict(self) -> dict[str, str | int | bool]:
        return {
            "id": self.rumor_id,
            "content": self.content,
            "truth_value": self.truth_value,
            "origin_location_id": self.origin_location_id,
            "spread_count": self.spread_count,
            "is_dead": self.is_dead,
            "created_date": self.created_date,
        }


class RumorPropagationRequest(BaseModel):
    """Request model for rumor propagation."""

    world_id: UUID = Field(..., description="World ID to propagate rumors in")
    batch_size: int = Field(default=500, ge=1, le=10000)


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
    """Response model for world rumors."""

    world_id: str
    rumors: list[RumorResponse]
    total_count: int
    active_count: int


def reset_world_state() -> None:
    """Reset in-memory rumor state for tests."""
    _rumor_store.clear()


@router.post("/rumors/propagate", response_model=dict)
async def propagate_rumors(propagation: RumorPropagationRequest) -> dict:
    """Advance rumors for a world using a lightweight in-memory model."""
    world_id = str(propagation.world_id)
    rumors = _rumor_store.setdefault(world_id, [])

    if not rumors:
        rumors.append(
            RumorState(
                rumor_id=f"rumor-{uuid4().hex[:12]}",
                content=f"Rumor wave initialized for world {world_id}",
                truth_value=70,
                origin_location_id="capital",
                spread_count=1,
                is_dead=False,
                created_date=datetime.now(UTC).isoformat(),
            )
        )
    else:
        for rumor in rumors[: propagation.batch_size]:
            rumor.spread_count += 1

    return {
        "world_id": world_id,
        "propagated_count": len(rumors),
        "rumors": [rumor.to_dict() for rumor in rumors],
    }


@router.get("/rumors/{world_id}", response_model=RumorListResponse)
async def get_active_rumors(world_id: UUID) -> RumorListResponse:
    """Return rumors previously propagated for a world."""
    rumors = _rumor_store.get(str(world_id), [])
    rumor_payloads = [RumorResponse(**rumor.to_dict()) for rumor in rumors]
    return RumorListResponse(
        world_id=str(world_id),
        rumors=rumor_payloads,
        total_count=len(rumor_payloads),
        active_count=len([rumor for rumor in rumor_payloads if rumor.is_dead is False]),
    )
