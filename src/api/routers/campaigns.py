from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
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

# Safe campaign ID pattern: alphanumeric, hyphens, underscores only
SAFE_CAMPAIGN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Allowed base directories for campaign files
_CAMPAIGN_ALLOWED_BASES = ["campaigns", "logs", "private/campaigns"]

# Campaign file registry - maps campaign_id to absolute file path
# This is populated by scanning allowed directories, never from user input
_CAMPAIGN_FILE_REGISTRY: dict[str, str] = {}


def _refresh_campaign_registry() -> None:
    """Scan allowed directories and populate the campaign file registry.

    This function builds a whitelist of valid campaign files by scanning
    the filesystem. User input is NEVER used to construct file paths -
    we only look up IDs in this pre-built registry.
    """
    global _CAMPAIGN_FILE_REGISTRY
    registry: dict[str, str] = {}

    for base_dir in _CAMPAIGN_ALLOWED_BASES:
        base_path = Path(base_dir)
        if not base_path.is_dir():
            continue

        # Scan for campaign files
        for file_path in base_path.iterdir():
            if not file_path.is_file():
                continue
            if file_path.suffix not in (".json", ".md"):
                continue

            # Extract campaign ID from filename (without extension)
            campaign_id = file_path.stem

            # Validate the ID matches our safe pattern
            if not SAFE_CAMPAIGN_ID_PATTERN.match(campaign_id):
                continue

            # Only register if not already registered (first match wins)
            if campaign_id not in registry:
                # Store the resolved absolute path
                registry[campaign_id] = str(file_path.resolve())

    _CAMPAIGN_FILE_REGISTRY = registry


def _get_campaign_file_from_registry(campaign_id: str) -> str | None:
    """Look up a campaign file path from the whitelist registry.

    This function ONLY returns paths that were discovered by scanning
    the filesystem - it never constructs paths from user input.

    Args:
        campaign_id: The campaign ID to look up.

    Returns:
        The absolute file path if found in registry, None otherwise.
    """
    # Refresh registry to pick up new/deleted files
    _refresh_campaign_registry()

    # Simple dictionary lookup - no path construction from user input
    return _CAMPAIGN_FILE_REGISTRY.get(campaign_id)


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
    """Retrieves a campaign by id.

    SECURITY: This endpoint uses a whitelist approach to prevent path injection.
    The campaign_id is looked up in a registry built from filesystem scans,
    never used directly to construct file paths.
    """
    # Look up campaign in the whitelist registry
    # This returns None if the ID isn't in our pre-scanned whitelist
    campaign_file = _get_campaign_file_from_registry(campaign_id)
    if not campaign_file:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        # campaign_file comes from our registry, not from user input
        # It was resolved to an absolute path during registry population
        file_path = Path(campaign_file)
        updated_at = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()

        if file_path.suffix == ".json":
            with open(file_path, "r") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("Campaign payload must be an object")
        else:
            with open(file_path, "r") as handle:
                payload = {"name": campaign_id, "description": handle.read().strip()}

        return _build_campaign_detail(campaign_id, payload, updated_at)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error retrieving campaign: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve campaign"
        ) from exc


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
