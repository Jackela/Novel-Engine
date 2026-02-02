from __future__ import annotations

import json
import logging
import os
import re
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

# Safe campaign ID pattern: alphanumeric, hyphens, underscores only
SAFE_CAMPAIGN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _sanitize_campaign_id(campaign_id: str) -> str:
    """
    Sanitize and validate campaign_id to prevent path traversal attacks.

    Returns the validated campaign_id if valid, raises HTTPException if invalid.
    This function ensures the returned value is safe for use in file paths.
    """
    if not campaign_id:
        raise HTTPException(status_code=400, detail="Campaign ID is required")
    if len(campaign_id) > 128:
        raise HTTPException(status_code=400, detail="Campaign ID too long (max 128 characters)")
    if not SAFE_CAMPAIGN_ID_PATTERN.match(campaign_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid campaign ID. Only alphanumeric characters, hyphens, and underscores are allowed.",
        )
    # Return a sanitized copy to make data flow explicit for static analysis
    return str(campaign_id)


def _validate_path_safety(file_path: str, allowed_bases: list[str]) -> bool:
    """
    Validate that a file path is within one of the allowed base directories.

    This is a critical security check to prevent path traversal attacks.
    Returns True if the path is safe, False otherwise.
    """
    abs_path = os.path.realpath(file_path)
    for base in allowed_bases:
        abs_base = os.path.realpath(base)
        # Ensure path is within base directory (handle both with and without trailing separator)
        if abs_path.startswith(abs_base + os.sep) or abs_path == abs_base:
            return True
    return False


# Allowed base directories for campaign files
_CAMPAIGN_ALLOWED_BASES = ["campaigns", "logs", "private/campaigns"]


def _find_campaign_file(safe_campaign_id: str) -> str | None:
    """
    Find campaign file by ID.

    Args:
        safe_campaign_id: A campaign ID that has been validated by _sanitize_campaign_id.
                         Must only contain alphanumeric, hyphens, and underscores.
    """
    # SECURITY: safe_campaign_id is pre-validated to contain only safe characters
    # No path traversal is possible with the validated pattern [a-zA-Z0-9_-]+
    for campaigns_path in _CAMPAIGN_ALLOWED_BASES:
        for extension in (".json", ".md"):
            # Using os.path.join with validated ID is safe
            candidate = os.path.join(campaigns_path, f"{safe_campaign_id}{extension}")
            # Additional safety: verify the resolved path is within expected directories
            if not _validate_path_safety(candidate, [campaigns_path]):
                continue  # Path traversal attempt blocked
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
    safe_id = _sanitize_campaign_id(campaign_id)
    campaign_file = _find_campaign_file(safe_id)
    if not campaign_file:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # SECURITY: Re-validate path safety before any file operations
    # This provides defense-in-depth against path traversal attacks
    if not _validate_path_safety(campaign_file, _CAMPAIGN_ALLOWED_BASES):
        logger.warning("Path validation failed for campaign file", extra={"safe_id": safe_id})
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        # Path is now validated - safe to perform file operations
        validated_path = os.path.realpath(campaign_file)
        updated_at = datetime.fromtimestamp(os.path.getmtime(validated_path)).isoformat()
        if validated_path.endswith(".json"):
            with open(validated_path, "r") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError("Campaign payload must be an object")
        else:
            with open(validated_path, "r") as handle:
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
