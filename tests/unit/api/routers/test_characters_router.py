"""
Unit tests for Character Router API

Tests cover:
- GET /characters - List characters
- GET /characters/{id} - Get character detail
- POST /characters - Create workspace character
- PUT /characters/{id} - Update character
- DELETE /characters/{id} - Delete character
- GET /characters/{id}/enhanced - Get enhanced character context
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routers.characters import router
from src.api.schemas import CharacterDetailResponse, CharacterSummary

pytestmark = pytest.mark.unit


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_characters_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for character files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_workspace_store() -> MagicMock:
    """Create a mock workspace character store."""
    store = MagicMock()
    store.list_ids.return_value = []
    return store


@pytest.fixture
def app_with_workspace(mock_workspace_store: MagicMock) -> FastAPI:
    """Create app with workspace store."""
    app = FastAPI()
    
    # Add workspace store to app state
    @app.middleware("http")
    async def add_workspace_store(request, call_next):
        request.app.state.workspace_character_store = mock_workspace_store
        response = await call_next(request)
        return response
    
    app.include_router(router, prefix="/api")
    return app


class TestGetCharacters:
    """Tests for GET /api/characters endpoint."""

    @patch("src.api.routers.characters.get_characters_directory_path")
    @patch("src.api.routers.characters._get_public_character_entries")
    def test_get_characters_empty(
        self, mock_get_entries, mock_get_path, client: TestClient, temp_characters_dir
    ) -> None:
        """Test getting characters when no characters exist."""
        mock_get_path.return_value = str(temp_characters_dir)
        mock_get_entries.return_value = []

        response = client.get("/api/characters")
        assert response.status_code == 200

        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) == 0

    @patch("src.api.routers.characters.get_characters_directory_path")
    @patch("src.api.routers.characters._get_public_character_entries")
    def test_get_characters_with_entries(
        self, mock_get_entries, mock_get_path, client: TestClient, temp_characters_dir
    ) -> None:
        """Test getting characters with existing entries."""
        mock_get_path.return_value = str(temp_characters_dir)
        
        # Create mock character entries
        timestamp = datetime.now()
        summary = CharacterSummary(
            id="char_001",
            agent_id="char_001",
            name="Test Character",
            status="active",
            type="character",
            updated_at=timestamp.isoformat(),
        )
        mock_get_entries.return_value = [(timestamp, summary)]

        response = client.get("/api/characters")
        assert response.status_code == 200

        data = response.json()
        assert len(data["characters"]) == 1
        assert data["characters"][0]["name"] == "Test Character"
        assert data["characters"][0]["id"] == "char_001"

    @patch("src.api.routers.characters.get_characters_directory_path")
    @patch("src.api.routers.characters._get_public_character_entries")
    def test_get_characters_with_workspace(
        self, mock_get_entries, mock_get_path, app: FastAPI, temp_characters_dir
    ) -> None:
        """Test getting characters with workspace_id header."""
        mock_get_path.return_value = str(temp_characters_dir)
        mock_get_entries.return_value = []

        # Create mock workspace store
        mock_store = MagicMock()
        mock_store.list_ids.return_value = ["workspace_char_001"]
        mock_store.get.return_value = {
            "id": "workspace_char_001",
            "name": "Workspace Character",
            "updated_at": datetime.now().isoformat(),
        }

        app.state.workspace_character_store = mock_store
        client = TestClient(app)

        response = client.get(
            "/api/characters",
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 200


class TestGetCharacterDetail:
    """Tests for GET /api/characters/{id} endpoint."""

    @patch("src.api.routers.characters.get_characters_directory_path")
    def test_get_character_not_found(
        self, mock_get_path, client: TestClient, temp_characters_dir
    ) -> None:
        """Test getting non-existent character."""
        mock_get_path.return_value = str(temp_characters_dir)

        response = client.get("/api/characters/nonexistent")
        assert response.status_code == 404

    @patch("src.api.routers.characters.get_characters_directory_path")
    def test_get_character_from_filesystem(
        self, mock_get_path, client: TestClient, temp_characters_dir
    ) -> None:
        """Test getting character from filesystem."""
        mock_get_path.return_value = str(temp_characters_dir)

        # Create character directory and files
        char_dir = temp_characters_dir / "test_character"
        char_dir.mkdir()
        
        char_file = char_dir / "character_test_character.md"
        char_file.write_text("# Test Character\n\nThis is a test character.")
        
        stats_file = char_dir / "stats.yaml"
        stats_file.write_text("skills:\n  strength: 10\nrelationships: {}\n")

        response = client.get("/api/characters/test_character")
        assert response.status_code == 200

        data = response.json()
        assert data["character_id"] == "test_character"
        assert data["name"] == "Test Character"

    def test_get_character_from_workspace(self, app: FastAPI) -> None:
        """Test getting character from workspace."""
        # Create mock workspace store
        mock_store = MagicMock()
        mock_store.get.return_value = {
            "id": "ws_char_001",
            "name": "Workspace Character",
            "background_summary": "Test background",
            "personality_traits": "Brave",
            "current_status": "active",
            "narrative_context": "Test context",
            "skills": {},
            "relationships": {},
            "current_location": "",
            "inventory": [],
            "metadata": {},
            "structured_data": {},
        }

        app.state.workspace_character_store = mock_store
        client = TestClient(app)

        response = client.get(
            "/api/characters/ws_char_001",
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["character_id"] == "ws_char_001"
        assert data["name"] == "Workspace Character"


class TestCreateCharacter:
    """Tests for POST /api/characters endpoint."""

    def test_create_character_success(self, app: FastAPI) -> None:
        """Test creating a new workspace character."""
        mock_store = MagicMock()
        mock_store.get.return_value = None  # Character doesn't exist
        mock_store.create.return_value = {
            "id": "new_char",
            "name": "New Character",
            "background_summary": "Test background",
            "personality_traits": "Kind",
            "skills": {"strength": 10},
            "relationships": {},
            "current_location": "Test Location",
            "inventory": ["sword"],
            "metadata": {"key": "value"},
            "structured_data": {},
            "current_status": "active",
            "narrative_context": "",
        }

        app.state.workspace_character_store = mock_store
        app.state.orchestrator = None
        client = TestClient(app)

        payload = {
            "agent_id": "new_char",
            "name": "New Character",
            "background_summary": "Test background",
            "personality_traits": "Kind",
            "skills": {"strength": 10},
            "relationships": {},
            "current_location": "Test Location",
            "inventory": ["sword"],
            "metadata": {"key": "value"},
            "structured_data": {},
        }

        response = client.post(
            "/api/characters",
            json=payload,
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 201

        data = response.json()
        assert data["character_id"] == "new_char"
        assert data["name"] == "New Character"

    def test_create_character_already_exists(self, app: FastAPI) -> None:
        """Test creating character that already exists."""
        mock_store = MagicMock()
        mock_store.get.return_value = {"id": "existing_char", "name": "Existing"}

        app.state.workspace_character_store = mock_store
        client = TestClient(app)

        payload = {
            "agent_id": "existing_char",
            "name": "New Character",
            "background_summary": "Test",
            "personality_traits": "",
        }

        response = client.post(
            "/api/characters",
            json=payload,
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 409

    def test_create_character_no_workspace_id(self, client: TestClient) -> None:
        """Test creating character without workspace ID."""
        payload = {
            "agent_id": "new_char",
            "name": "New Character",
            "background_summary": "Test",
            "personality_traits": "",
        }

        response = client.post("/api/characters", json=payload)
        assert response.status_code == 422  # Missing required header

    def test_create_character_store_unavailable(self, app: FastAPI) -> None:
        """Test creating character when store is unavailable."""
        app.state.workspace_character_store = None
        client = TestClient(app)

        payload = {
            "agent_id": "new_char",
            "name": "New Character",
            "background_summary": "Test",
            "personality_traits": "",
        }

        response = client.post(
            "/api/characters",
            json=payload,
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 503


class TestUpdateCharacter:
    """Tests for PUT /api/characters/{id} endpoint."""

    def test_update_character_success(self, app: FastAPI) -> None:
        """Test updating a workspace character."""
        mock_store = MagicMock()
        mock_store.update.return_value = {
            "id": "char_001",
            "name": "Updated Name",
            "background_summary": "Updated background",
            "personality_traits": "Updated traits",
            "skills": {},
            "relationships": {},
            "current_location": "",
            "inventory": [],
            "metadata": {},
            "structured_data": {},
            "current_status": "active",
            "narrative_context": "",
        }

        app.state.workspace_character_store = mock_store
        client = TestClient(app)

        payload = {"name": "Updated Name", "background_summary": "Updated background"}

        response = client.put(
            "/api/characters/char_001",
            json=payload,
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Name"

    def test_update_character_not_found(self, app: FastAPI) -> None:
        """Test updating non-existent character."""
        mock_store = MagicMock()
        mock_store.update.side_effect = FileNotFoundError("Character not found")

        app.state.workspace_character_store = mock_store
        client = TestClient(app)

        payload = {"name": "Updated Name"}

        response = client.put(
            "/api/characters/nonexistent",
            json=payload,
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 404


class TestDeleteCharacter:
    """Tests for DELETE /api/characters/{id} endpoint."""

    def test_delete_character_success(self, app: FastAPI) -> None:
        """Test deleting a workspace character."""
        mock_store = MagicMock()
        mock_store.delete.return_value = None

        app.state.workspace_character_store = mock_store
        app.state.orchestrator = None
        client = TestClient(app)

        response = client.delete(
            "/api/characters/char_001",
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 204

    def test_delete_character_not_found(self, app: FastAPI) -> None:
        """Test deleting non-existent character."""
        mock_store = MagicMock()
        mock_store.delete.side_effect = ValueError("Character not found")

        app.state.workspace_character_store = mock_store
        client = TestClient(app)

        response = client.delete(
            "/api/characters/nonexistent",
            headers={"X-Workspace-ID": "test-workspace"}
        )
        assert response.status_code == 400


class TestGetCharacterEnhanced:
    """Tests for GET /api/characters/{id}/enhanced endpoint."""

    def test_get_character_enhanced(self, client: TestClient) -> None:
        """Test getting enhanced character context."""
        response = client.get("/api/characters/test_char/enhanced")
        assert response.status_code == 200

        data = response.json()
        assert data["character_id"] == "test_char"
        assert "enhanced_context" in data
        assert "psychological_profile" in data
        assert "tactical_analysis" in data

    def test_get_character_enhanced_with_special_chars(self, client: TestClient) -> None:
        """Test getting enhanced context with special character IDs."""
        response = client.get("/api/characters/my_character_123/enhanced")
        assert response.status_code == 200

        data = response.json()
        assert data["character_id"] == "my_character_123"
        # Verify display name is properly formatted
        assert "My Character 123" in data["enhanced_context"]


class TestCharacterHelpers:
    """Tests for character router helper functions."""

    def test_workspace_record_to_character_detail(self) -> None:
        """Test converting workspace record to character detail."""
        from src.api.routers.characters import _workspace_record_to_character_detail

        record = {
            "id": "char_001",
            "name": "Test Character",
            "background_summary": "Test background",
            "personality_traits": "Brave, Kind",
            "current_status": "active",
            "narrative_context": "Test context",
            "skills": {"strength": 10},
            "relationships": {"friend": 80},
            "current_location": "Town Square",
            "inventory": ["sword", "shield"],
            "metadata": {"level": 5},
            "structured_data": {"class": "warrior"},
        }

        result = _workspace_record_to_character_detail(record)

        assert isinstance(result, CharacterDetailResponse)
        assert result.character_id == "char_001"
        assert result.name == "Test Character"
        assert result.skills == {"strength": 10}
        assert result.inventory == ["sword", "shield"]

    def test_workspace_record_with_defaults(self) -> None:
        """Test converting record with minimal data."""
        from src.api.routers.characters import _workspace_record_to_character_detail

        record = {"id": "minimal_char"}

        result = _workspace_record_to_character_detail(record)

        assert result.character_id == "minimal_char"
        assert result.name == "minimal_char"  # Falls back to ID
        assert result.skills == {}
        assert result.relationships == {}
