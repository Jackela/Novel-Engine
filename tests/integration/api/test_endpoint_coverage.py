#!/usr/bin/env python3
"""
Endpoint coverage tests for key API routes.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.services.paths import get_characters_directory_path


@pytest.mark.integration
def test_character_detail_endpoint_returns_shape():
    """Validate /api/characters/{id} returns the detail schema."""
    app = create_app()
    character_dir = Path(get_characters_directory_path())
    character_id = next(
        (item.name for item in character_dir.iterdir() if item.is_dir()),
        "pilot",
    )

    with TestClient(app) as client:
        response = client.get(f"/api/characters/{character_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["character_id"] == character_id
    assert payload["agent_id"] == character_id
    assert payload["name"]
    assert "background_summary" in payload
    assert "personality_traits" in payload


@pytest.mark.integration
def test_orchestration_status_endpoint_returns_status():
    """Validate /api/orchestration/status returns the status envelope."""
    app = create_app()
    app.state.api_service = MagicMock()
    app.state.api_service.get_status = AsyncMock(
        return_value={
            "status": "idle",
            "current_turn": 0,
            "total_turns": 0,
            "queue_length": 0,
            "average_processing_time": 0.0,
            "steps": [],
        }
    )

    with TestClient(app) as client:
        response = client.get("/api/orchestration/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["status"] == "idle"


@pytest.mark.integration
def test_campaign_detail_endpoint_returns_campaign():
    """Validate /api/campaigns/{id} returns campaign detail."""
    app = create_app()
    campaigns_dir = Path("campaigns")
    campaigns_dir.mkdir(exist_ok=True)
    campaign_id = "campaign_test_endpoint"
    campaign_file = campaigns_dir / f"{campaign_id}.json"
    campaign_file.write_text(
        '{"id":"campaign_test_endpoint","name":"Test Campaign","description":"Test","status":"active","created_at":"2024-01-01T00:00:00","current_turn":1}',
        encoding="utf-8",
    )

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/campaigns/{campaign_id}")
    finally:
        campaign_file.unlink(missing_ok=True)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == campaign_id
    assert payload["name"] == "Test Campaign"
    assert payload["status"] == "active"
    assert "updated_at" in payload
