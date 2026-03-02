"""Integration tests for Campaigns API endpoints.

Tests campaign management including listing, retrieval, and creation.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Set testing mode BEFORE importing app
os.environ["ORCHESTRATOR_MODE"] = "testing"

from src.api.app import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    """Create a test client for the Campaigns API."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def temp_campaign_dir():
    """Create a temporary campaigns directory for isolation."""
    # Create temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        campaigns_dir = Path(tmpdir) / "campaigns"
        campaigns_dir.mkdir()

        # Store original working directory
        original_cwd = os.getcwd()

        # Change to temp directory
        os.chdir(tmpdir)

        yield campaigns_dir

        # Restore original directory
        os.chdir(original_cwd)


class TestListCampaignsEndpoint:
    """Tests for GET /api/campaigns endpoint."""

    def test_list_campaigns_empty(self, client):
        """Test listing campaigns when none exist."""
        response = client.get("/api/campaigns")

        assert response.status_code == 200
        data = response.json()

        assert "campaigns" in data
        assert isinstance(data["campaigns"], list)

    def test_list_campaigns_success(self, client, temp_campaign_dir):
        """Test listing campaigns returns available campaigns."""
        # Create a test campaign file
        campaign_file = temp_campaign_dir / "test_campaign.json"
        campaign_file.write_text(json.dumps({"name": "Test Campaign"}))

        response = client.get("/api/campaigns")

        assert response.status_code == 200
        data = response.json()

        assert "campaigns" in data
        assert isinstance(data["campaigns"], list)

        # Should find our test campaign
        campaign_names = data["campaigns"]
        assert "test_campaign" in campaign_names

    def test_list_campaigns_includes_json_and_md(self, client, temp_campaign_dir):
        """Test that listing includes both JSON and markdown files."""
        # Create both types
        (temp_campaign_dir / "campaign_json.json").write_text(
            json.dumps({"name": "JSON Campaign"})
        )
        (temp_campaign_dir / "campaign_md.md").write_text("# Markdown Campaign")

        response = client.get("/api/campaigns")

        assert response.status_code == 200
        data = response.json()

        campaign_names = data["campaigns"]
        assert "campaign_json" in campaign_names
        assert "campaign_md" in campaign_names

    def test_list_campaigns_sorted_alphabetically(self, client, temp_campaign_dir):
        """Test that campaigns are returned in sorted order."""
        # Create campaigns in non-alphabetical order
        (temp_campaign_dir / "zeta_campaign.json").write_text("{}")
        (temp_campaign_dir / "alpha_campaign.json").write_text("{}")
        (temp_campaign_dir / "beta_campaign.json").write_text("{}")

        response = client.get("/api/campaigns")

        assert response.status_code == 200
        data = response.json()

        campaigns = data["campaigns"]
        assert campaigns == sorted(campaigns)


class TestGetCampaignEndpoint:
    """Tests for GET /api/campaigns/{campaign_id} endpoint."""

    def test_get_campaign_not_found(self, client):
        """Test getting non-existent campaign returns 404."""
        response = client.get("/api/campaigns/nonexistent_campaign")

        assert response.status_code == 404

    def test_get_campaign_json_success(self, client, temp_campaign_dir):
        """Test getting a JSON campaign file."""
        campaign_data = {
            "name": "Test Adventure",
            "description": "A test campaign",
            "status": "active",
            "current_turn": 5,
        }
        campaign_file = temp_campaign_dir / "test_adventure.json"
        campaign_file.write_text(json.dumps(campaign_data))

        response = client.get("/api/campaigns/test_adventure")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "test_adventure"
        assert data["name"] == "Test Adventure"
        assert data["description"] == "A test campaign"
        assert data["status"] == "active"
        assert data["current_turn"] == 5
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_campaign_markdown_success(self, client, temp_campaign_dir):
        """Test getting a markdown campaign file."""
        campaign_file = temp_campaign_dir / "markdown_campaign.md"
        campaign_file.write_text("# My Campaign\n\nThis is a markdown campaign.")

        response = client.get("/api/campaigns/markdown_campaign")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == "markdown_campaign"
        assert "name" in data
        assert "description" in data

    def test_get_campaign_with_path_injection_fails(self, client):
        """Test that path injection attempts are rejected."""
        # Try various path traversal patterns
        malicious_ids = [
            "../etc/passwd",
            "..%2F..%2Fetc%2Fpasswd",
            "....//....//etc/passwd",
        ]

        for campaign_id in malicious_ids:
            response = client.get(f"/api/campaigns/{campaign_id}")

            # Should return 404 (not in registry) or 400 (invalid characters)
            assert response.status_code in [400, 404]

    def test_get_campaign_invalid_characters(self, client):
        """Test that campaign IDs with invalid characters are handled."""
        response = client.get("/api/campaigns/../../secret")

        assert response.status_code in [400, 404]


class TestCreateCampaignEndpoint:
    """Tests for POST /api/campaigns endpoint."""

    def test_create_campaign_success(self, client, temp_campaign_dir):
        """Test successful campaign creation."""
        response = client.post(
            "/api/campaigns",
            json={
                "name": "New Adventure",
                "description": "A brand new campaign",
                "participants": ["player1", "player2"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "campaign_id" in data
        assert data["name"] == "New Adventure"
        assert data["status"] == "created"
        assert "created_at" in data

        # Verify campaign_id format
        assert data["campaign_id"].startswith("campaign_")

    def test_create_campaign_minimal(self, client, temp_campaign_dir):
        """Test creating campaign with minimal data."""
        response = client.post(
            "/api/campaigns",
            json={"name": "Minimal Campaign"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "campaign_id" in data
        assert data["name"] == "Minimal Campaign"

    def test_create_campaign_missing_name_returns_422(self, client):
        """Test that missing name returns validation error."""
        response = client.post(
            "/api/campaigns",
            json={"description": "No name provided"},
        )

        assert response.status_code == 422

    def test_create_campaign_persists_file(self, client, temp_campaign_dir):
        """Test that created campaign is persisted to file."""
        response = client.post(
            "/api/campaigns",
            json={
                "name": "Persistent Campaign",
                "description": "Should be saved to disk",
            },
        )

        assert response.status_code == 200
        campaign_id = response.json()["campaign_id"]

        # Verify file exists
        campaign_file = temp_campaign_dir / f"{campaign_id}.json"
        assert campaign_file.exists()

        # Verify file content
        with open(campaign_file) as f:
            saved_data = json.load(f)

        assert saved_data["name"] == "Persistent Campaign"
        assert saved_data["description"] == "Should be saved to disk"

    def test_create_campaign_with_empty_participants(self, client, temp_campaign_dir):
        """Test creating campaign with empty participants list."""
        response = client.post(
            "/api/campaigns",
            json={
                "name": "Solo Campaign",
                "description": "No participants",
                "participants": [],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "campaign_id" in data

    def test_create_campaign_generates_unique_ids(self, client, temp_campaign_dir):
        """Test that each created campaign gets a unique ID."""
        response1 = client.post(
            "/api/campaigns",
            json={"name": "Campaign 1"},
        )
        response2 = client.post(
            "/api/campaigns",
            json={"name": "Campaign 2"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        id1 = response1.json()["campaign_id"]
        id2 = response2.json()["campaign_id"]

        assert id1 != id2


class TestCampaignCRUDFlow:
    """Tests for full CRUD workflow."""

    def test_create_and_retrieve_campaign(self, client, temp_campaign_dir):
        """Test creating and then retrieving a campaign."""
        # Create
        create_response = client.post(
            "/api/campaigns",
            json={
                "name": "Full Flow Campaign",
                "description": "Testing the full flow",
                "participants": ["alice", "bob"],
            },
        )

        assert create_response.status_code == 200
        campaign_id = create_response.json()["campaign_id"]

        # Retrieve
        get_response = client.get(f"/api/campaigns/{campaign_id}")

        assert get_response.status_code == 200
        data = get_response.json()

        assert data["id"] == campaign_id
        assert data["name"] == "Full Flow Campaign"

    def test_list_after_create(self, client, temp_campaign_dir):
        """Test that created campaigns appear in list."""
        # Create a campaign
        create_response = client.post(
            "/api/campaigns",
            json={"name": "List Test Campaign"},
        )

        assert create_response.status_code == 200
        campaign_id = create_response.json()["campaign_id"]

        # List campaigns
        list_response = client.get("/api/campaigns")

        assert list_response.status_code == 200
        campaigns = list_response.json()["campaigns"]

        # Extract campaign ID from full ID (campaign_XXXXX -> XXXXX)
        # The list returns the stem (filename without extension)
        assert campaign_id in campaigns
