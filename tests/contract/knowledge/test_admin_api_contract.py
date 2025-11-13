"""
Contract Tests for Knowledge Management Admin API

TDD Approach: Tests written FIRST, must FAIL before implementation.
These tests verify API contracts match specification.

Constitution Compliance:
- Article III (TDD): Red-Green-Refactor cycle
- FR-002, FR-003, FR-004: CRUD API endpoints
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

# NOTE: These imports will fail until API is implemented
try:
    from backend.api.main import app  # FastAPI application
except ImportError:
    app = None


pytestmark = [pytest.mark.knowledge, pytest.mark.api, pytest.mark.requires_services]


@pytest_asyncio.fixture
async def client():
    """Create test client for API testing."""
    if app is None:
        pytest.skip("FastAPI app not yet implemented (TDD - expected to fail)")

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Authentication headers for admin user."""
    # TODO: Implement actual authentication when auth middleware is ready
    return {
        "Authorization": "Bearer test-admin-token",
        "X-User-ID": "test-admin-001",
        "X-User-Role": "admin",
    }


class TestPostKnowledgeEntriesEndpoint:
    """Contract tests for POST /api/v1/knowledge/entries (FR-002)."""

    @pytest.mark.asyncio
    async def test_create_entry_success_returns_201(self, client, auth_headers):
        """Test successful entry creation returns 201 Created."""
        # Arrange
        payload = {
            "content": "Test character profile content",
            "knowledge_type": "profile",
            "owning_character_id": "char-001",
            "access_level": "public",
        }

        # Act
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "entry_id" in data
        assert "created_at" in data
        assert data["content"] == payload["content"]
        assert data["knowledge_type"] == payload["knowledge_type"]

    @pytest.mark.asyncio
    async def test_create_entry_with_empty_content_returns_400(
        self, client, auth_headers
    ):
        """Test creating entry with empty content returns 400 Bad Request."""
        # Arrange
        payload = {
            "content": "",  # Empty content
            "knowledge_type": "profile",
            "owning_character_id": "char-001",
            "access_level": "public",
        }

        # Act
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data

    @pytest.mark.asyncio
    async def test_create_entry_with_invalid_knowledge_type_returns_400(
        self, client, auth_headers
    ):
        """Test creating entry with invalid knowledge_type returns 400."""
        # Arrange
        payload = {
            "content": "Test content",
            "knowledge_type": "invalid_type",  # Invalid enum value
            "owning_character_id": "char-001",
            "access_level": "public",
        }

        # Act
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_entry_with_character_specific_access(
        self, client, auth_headers
    ):
        """Test creating entry with CHARACTER_SPECIFIC access level."""
        # Arrange
        payload = {
            "content": "Private character information",
            "knowledge_type": "memory",
            "owning_character_id": "char-001",
            "access_level": "character_specific",
            "allowed_character_ids": ["char-001", "char-002"],
        }

        # Act
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["access_level"] == "character_specific"
        assert "char-001" in data["allowed_character_ids"]

    @pytest.mark.asyncio
    async def test_create_entry_with_role_based_access(self, client, auth_headers):
        """Test creating entry with ROLE_BASED access level."""
        # Arrange
        payload = {
            "content": "Engineering documentation",
            "knowledge_type": "lore",
            "owning_character_id": None,  # World knowledge
            "access_level": "role_based",
            "allowed_roles": ["engineer", "medical"],
        }

        # Act
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["access_level"] == "role_based"
        assert "engineer" in data["allowed_roles"]

    @pytest.mark.asyncio
    async def test_create_entry_without_auth_returns_401(self, client):
        """Test creating entry without authentication returns 401 Unauthorized."""
        # Arrange
        payload = {
            "content": "Test content",
            "knowledge_type": "profile",
            "owning_character_id": "char-001",
            "access_level": "public",
        }

        # Act - no auth headers
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_entry_without_admin_role_returns_403(self, client):
        """Test creating entry without admin/game_master role returns 403 Forbidden."""
        # Arrange
        payload = {
            "content": "Test content",
            "knowledge_type": "profile",
            "owning_character_id": "char-001",
            "access_level": "public",
        }
        non_admin_headers = {
            "Authorization": "Bearer test-user-token",
            "X-User-ID": "test-user-001",
            "X-User-Role": "player",  # Not admin or game_master
        }

        # Act
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=non_admin_headers,
        )

        # Assert
        assert response.status_code == 403


class TestPutKnowledgeEntriesEndpoint:
    """Contract tests for PUT /api/v1/knowledge/entries/{id} (FR-003)."""

    @pytest_asyncio.fixture
    async def existing_entry_id(self, client, auth_headers):
        """Create an entry for update tests."""
        # Create entry first
        payload = {
            "content": "Original content",
            "knowledge_type": "profile",
            "owning_character_id": "char-001",
            "access_level": "public",
        }
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )
        return response.json()["entry_id"]

    @pytest.mark.asyncio
    async def test_update_entry_success_returns_200(
        self, client, auth_headers, existing_entry_id
    ):
        """Test successful entry update returns 200 OK."""
        # Arrange
        payload = {
            "content": "Updated content for testing",
        }

        # Act
        response = await client.put(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == payload["content"]
        assert data["entry_id"] == existing_entry_id
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_update_entry_with_empty_content_returns_400(
        self, client, auth_headers, existing_entry_id
    ):
        """Test updating entry with empty content returns 400 Bad Request."""
        # Arrange
        payload = {
            "content": "",  # Empty content
        }

        # Act
        response = await client.put(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_non_existent_entry_returns_404(self, client, auth_headers):
        """Test updating non-existent entry returns 404 Not Found."""
        # Arrange
        non_existent_id = str(uuid4())
        payload = {
            "content": "Updated content",
        }

        # Act
        response = await client.put(
            f"/api/v1/knowledge/entries/{non_existent_id}",
            json=payload,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_entry_without_auth_returns_401(
        self, client, existing_entry_id
    ):
        """Test updating entry without authentication returns 401."""
        # Arrange
        payload = {
            "content": "Updated content",
        }

        # Act
        response = await client.put(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            json=payload,
        )

        # Assert
        assert response.status_code == 401


class TestDeleteKnowledgeEntriesEndpoint:
    """Contract tests for DELETE /api/v1/knowledge/entries/{id} (FR-004)."""

    @pytest_asyncio.fixture
    async def existing_entry_id(self, client, auth_headers):
        """Create an entry for delete tests."""
        payload = {
            "content": "Entry to be deleted",
            "knowledge_type": "memory",
            "owning_character_id": "char-001",
            "access_level": "public",
        }
        response = await client.post(
            "/api/v1/knowledge/entries",
            json=payload,
            headers=auth_headers,
        )
        return response.json()["entry_id"]

    @pytest.mark.asyncio
    async def test_delete_entry_success_returns_204(
        self, client, auth_headers, existing_entry_id
    ):
        """Test successful entry deletion returns 204 No Content."""
        # Act
        response = await client.delete(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_entry_removes_from_database(
        self, client, auth_headers, existing_entry_id
    ):
        """Test that deleted entry cannot be retrieved."""
        # Act - delete entry
        await client.delete(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            headers=auth_headers,
        )

        # Assert - entry should not be retrievable
        get_response = await client.get(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_non_existent_entry_returns_404(self, client, auth_headers):
        """Test deleting non-existent entry returns 404 Not Found."""
        # Arrange
        non_existent_id = str(uuid4())

        # Act
        response = await client.delete(
            f"/api/v1/knowledge/entries/{non_existent_id}",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_entry_without_auth_returns_401(
        self, client, existing_entry_id
    ):
        """Test deleting entry without authentication returns 401."""
        # Act
        response = await client.delete(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_entry_is_idempotent(
        self, client, auth_headers, existing_entry_id
    ):
        """Test that deleting already deleted entry succeeds (idempotent)."""
        # Act - delete twice
        response1 = await client.delete(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            headers=auth_headers,
        )
        response2 = await client.delete(
            f"/api/v1/knowledge/entries/{existing_entry_id}",
            headers=auth_headers,
        )

        # Assert - first succeeds, second returns 404 (entry already gone)
        assert response1.status_code == 204
        assert response2.status_code == 404
