from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from src.api.schemas import CampaignCreationRequest, CampaignCreationResponse, CampaignsListResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["campaigns"])


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

