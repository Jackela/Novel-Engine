from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from src.api.schemas import (
    CampaignCreationRequest,
    CampaignCreationResponse,
    CampaignDetailResponse,
    CampaignsListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Campaigns"])


def _find_campaign_file(campaign_id: str) -> str | None:
    campaigns_paths = ["campaigns", "logs", "private/campaigns"]
    for campaigns_path in campaigns_paths:
        for extension in (".json", ".md"):
            candidate = os.path.join(campaigns_path, f"{campaign_id}{extension}")
            if os.path.isfile(candidate):
                return candidate
    return None


def _build_campaign_detail(campaign_id: str, payload: dict[str, Any], updated_at: str) -> CampaignDetailResponse:
    created_at = str(payload.get("created_at") or updated_at)
    return CampaignDetailResponse(
        id=campaign_id,
        name=str(payload.get("name") or campaign_id),
        description=str(payload.get("description") or ""),
        status=str(payload.get("status") or "active"),
        created_at=created_at,
        updated_at=str(payload.get("updated_at") or updated_at),
        current_turn=int(payload.get("current_turn") or 0),
    )


@router.get("/campaigns", response_model=CampaignsListResponse)
async def get_campaigns() -> CampaignsListResponse:
    """Retrieves a list of available campaigns."""
    try:
        campaigns_paths = ["campaigns", "logs", "private/campaigns"]
        campaigns: list[str] = []

        for campaigns_path in campaigns_paths:
            if os.path.isdir(campaigns_path):
                for item in os.listdir(campaigns_path):
                    if item.endswith(".md") or item.endswith(".json"):
                        campaign_name = item.replace(".md", "").replace(".json", "")
                        if campaign_name not in campaigns:
                            campaigns.append(campaign_name)

        campaigns = sorted(campaigns)
        logger.info("Found %d campaigns: %s", len(campaigns), campaigns)
        return CampaignsListResponse(campaigns=campaigns)

    except Exception as exc:
        logger.error("Error retrieving campaigns: %s", exc, exc_info=True)
        return CampaignsListResponse(campaigns=[])


@router.get("/campaigns/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(campaign_id: str) -> CampaignDetailResponse:
    """Retrieves a campaign by id."""
    campaign_file = _find_campaign_file(campaign_id)
    if not campaign_file:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        updated_at = datetime.fromtimestamp(os.path.getmtime(campaign_file)).isoformat()
        if campaign_file.endswith(".json"):
            with open(campaign_file, "r") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("Campaign payload must be an object")
        else:
            with open(campaign_file, "r") as handle:
                payload = {"name": campaign_id, "description": handle.read().strip()}
        return _build_campaign_detail(campaign_id, payload, updated_at)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving campaign: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve campaign") from exc


@router.post("/campaigns", response_model=CampaignCreationResponse)
async def create_campaign(request: CampaignCreationRequest) -> CampaignCreationResponse:
    """Creates a new campaign."""
    try:
        campaign_id = f"campaign_{uuid.uuid4().hex[:8]}"
        campaigns_dir = "campaigns"
        os.makedirs(campaigns_dir, exist_ok=True)

        campaign_file = os.path.join(campaigns_dir, f"{campaign_id}.json")
        campaign_data: dict[str, Any] = {
            "id": campaign_id,
            "name": request.name,
            "description": request.description or "",
            "participants": request.participants,
            "created_at": datetime.now().isoformat(),
            "status": "created",
        }

        with open(campaign_file, "w") as handle:
            json.dump(campaign_data, handle, indent=2)

        logger.info("Created campaign %s", campaign_id)
        return CampaignCreationResponse(
            campaign_id=campaign_id,
            name=request.name,
            status="created",
            created_at=campaign_data["created_at"],
        )

    except Exception as exc:
        logger.error("Error creating campaign: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create campaign: {exc}")
