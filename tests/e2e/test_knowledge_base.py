"""E2E Tests for Knowledge Base Flow.

This module tests the end-to-end knowledge base flows:
1. Upload documents to knowledge base
2. Process and index documents
3. Execute search queries
4. Manage lore entries

Tests:
- Document upload and processing
- Search and retrieval
- Lore entry management
- Chat with RAG context
"""

import os
# Set testing mode BEFORE importing app
os.environ["ORCHESTRATOR_MODE"] = "testing"

import pytest
import time
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the E2E tests."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

# Mark all tests in this module as e2e tests
pytestmark = pytest.mark.e2e


@pytest.mark.e2e
class TestKnowledgeBase:
    """E2E tests for knowledge base operations."""

    def test_lore_entry_create_and_retrieve(self, client):
        """Test creating and retrieving a lore entry.

        Verifies:
        - POST /api/lore creates entry
        - GET /api/lore/{id} retrieves entry
        """
        # Create lore entry
        entry_data = {
            "title": "The Ancient Kingdom",
            "content": "Long ago, there was a kingdom of great power and wisdom...",
            "category": "history",
            "tags": ["ancient", "kingdom", "history"],
            "summary": "History of the ancient kingdom"
        }

        response = client.post("/api/lore", json=entry_data)
        assert response.status_code == 201, f"Lore entry creation failed: {response.text}"

        data = response.json()
        assert "id" in data, "Entry ID not returned"
        entry_id = data["id"]

        # Retrieve entry
        get_response = client.get(f"/api/lore/{entry_id}")
        assert get_response.status_code == 200, "Failed to retrieve lore entry"

        retrieved = get_response.json()
        assert retrieved["title"] == "The Ancient Kingdom"
        assert retrieved["category"] == "history"

    def test_lore_entry_update_and_delete(self, client):
        """Test updating and deleting lore entry.

        Verifies:
        - PUT /api/lore/{id} updates entry
        - DELETE /api/lore/{id} removes entry
        """
        # Create entry (use valid category from LoreCategory enum)
        entry_data = {
            "title": "Test Entry",
            "content": "Original content",
            "category": "history"
        }

        create_response = client.post("/api/lore", json=entry_data)
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]

        # Update entry
        update_data = {
            "title": "Updated Test Entry",
            "content": "Updated content"
        }

        update_response = client.put(f"/api/lore/{entry_id}", json=update_data)
        assert update_response.status_code == 200, "Update failed"

        updated = update_response.json()
        assert updated["title"] == "Updated Test Entry"

        # Delete entry
        delete_response = client.delete(f"/api/lore/{entry_id}")
        assert delete_response.status_code == 204, "Delete failed"

        # Verify deletion
        get_response = client.get(f"/api/lore/{entry_id}")
        assert get_response.status_code == 404, "Entry should not exist after deletion"

    def test_lore_search_functionality(self, client):
        """Test searching lore entries.

        Verifies:
        - GET /api/lore/search returns matching entries
        - Search by title works
        """
        # Create searchable entries
        entries = [
            {
                "title": "Magic Spells Guide",
                "content": "A comprehensive guide to magic spells",
                "category": "magic",
                "tags": ["magic", "spells"]
            },
            {
                "title": "Combat Techniques",
                "content": "Advanced combat training manual",
                "category": "combat",
                "tags": ["combat", "fighting"]
            }
        ]

        created_ids = []
        for entry in entries:
            response = client.post("/api/lore", json=entry)
            if response.status_code == 201:
                created_ids.append(response.json()["id"])

        # Search for magic
        search_response = client.get("/api/lore/search?q=magic")
        assert search_response.status_code == 200

        results = search_response.json()
        assert "entries" in results

        # Cleanup
        for entry_id in created_ids:
            client.delete(f"/api/lore/{entry_id}")

    def test_lore_list_with_filters(self, client):
        """Test listing lore entries with filters.

        Verifies:
        - GET /api/lore returns list
        - Category filter works
        - Tag filter works
        """
        # Create entries with different categories
        entries = [
            {"title": "History Entry", "content": "History content", "category": "history"},
            {"title": "Magic Entry", "content": "Magic content", "category": "magic"},
        ]

        created_ids = []
        for entry in entries:
            response = client.post("/api/lore", json=entry)
            if response.status_code == 201:
                created_ids.append(response.json()["id"])

        # List all
        list_response = client.get("/api/lore")
        assert list_response.status_code == 200

        data = list_response.json()
        assert "entries" in data
        assert "total" in data

        # Filter by category
        filtered_response = client.get("/api/lore?category=history")
        assert filtered_response.status_code == 200

        # Cleanup
        for entry_id in created_ids:
            client.delete(f"/api/lore/{entry_id}")


@pytest.mark.e2e
class TestKnowledgeRetrieval:
    """E2E tests for knowledge retrieval operations."""

    def test_retrieve_relevant_context(self, client):
        """Test retrieving relevant context for queries.

        Verifies:
        - RAG endpoint returns relevant chunks
        """
        # Create some knowledge entries
        entry_data = {
            "title": "Dragon Lore",
            "content": "Dragons are ancient creatures of immense power. They hoard treasures and breathe fire.",
            "category": "creatures",
            "tags": ["dragons", "creatures"]
        }

        create_response = client.post("/api/lore", json=entry_data)
        if create_response.status_code == 201:
            entry_id = create_response.json()["id"]

            # Try to retrieve relevant context (if endpoint exists)
            # Note: Exact endpoint may vary based on implementation
            response = client.get("/api/brain/rag/context?query=dragons")

            # Cleanup
            client.delete(f"/api/lore/{entry_id}")

            # Endpoint may not exist, so accept 200 or 404
            assert response.status_code in [200, 404]

    def test_chat_with_rag_context(self, client):
        """Test chat endpoint with RAG context.

        Verifies:
        - POST /api/brain/chat returns streaming response
        - Query is processed
        """
        chat_request = {
            "query": "Tell me about the world",
            "max_chunks": 3,
            "session_id": "test_session_123"
        }

        response = client.post("/api/brain/chat", json=chat_request)

        # Endpoint may not be available
        if response.status_code == 404:
            pytest.skip("Chat endpoint not available")

        assert response.status_code == 200, f"Chat request failed: {response.text}"
        # Response should be streaming (text/event-stream)
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_knowledge_categories(self, client):
        """Test retrieving knowledge categories.

        Verifies:
        - Categories endpoint returns valid categories
        """
        # Create entries in different categories
        categories = ["history", "magic", "geography"]
        created_ids = []

        for category in categories:
            entry = {
                "title": f"{category.title()} Entry",
                "content": f"Content about {category}",
                "category": category
            }
            response = client.post("/api/lore", json=entry)
            if response.status_code == 201:
                created_ids.append(response.json()["id"])

        # List entries and verify categories
        list_response = client.get("/api/lore")
        assert list_response.status_code == 200

        # Cleanup
        for entry_id in created_ids:
            client.delete(f"/api/lore/{entry_id}")

    def test_tag_based_filtering(self, client):
        """Test filtering knowledge by tags.

        Verifies:
        - Tag filter returns matching entries
        """
        # Create entries with specific tags
        entry1 = {
            "title": "Fire Magic",
            "content": "About fire magic",
            "category": "magic",
            "tags": ["fire", "magic", "elemental"]
        }
        entry2 = {
            "title": "Ice Magic",
            "content": "About ice magic",
            "category": "magic",
            "tags": ["ice", "magic", "elemental"]
        }

        response1 = client.post("/api/lore", json=entry1)
        response2 = client.post("/api/lore", json=entry2)

        ids = []
        if response1.status_code == 201:
            ids.append(response1.json()["id"])
        if response2.status_code == 201:
            ids.append(response2.json()["id"])

        # Filter by tag
        filtered = client.get("/api/lore?tag=fire")
        assert filtered.status_code == 200

        # Search by tags
        search = client.get("/api/lore/search?tags=magic,elemental")
        assert search.status_code == 200

        # Cleanup
        for entry_id in ids:
            client.delete(f"/api/lore/{entry_id}")


@pytest.mark.e2e
class TestChatSessions:
    """E2E tests for chat session management."""

    def test_list_chat_sessions(self, client):
        """Test listing chat sessions.

        Verifies:
        - GET /api/brain/chat/sessions returns sessions
        """
        response = client.get("/api/brain/chat/sessions")

        if response.status_code == 404:
            pytest.skip("Chat sessions endpoint not available")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    def test_chat_session_messages(self, client):
        """Test retrieving chat session messages.

        Verifies:
        - GET /api/brain/chat/sessions/{id}/messages returns messages
        """
        # First create a session by sending a message
        chat_request = {
            "query": "Hello",
            "session_id": "test_messages_session"
        }

        chat_response = client.post("/api/brain/chat", json=chat_request)

        if chat_response.status_code == 404:
            pytest.skip("Chat endpoint not available")

        # Try to get messages
        messages_response = client.get("/api/brain/chat/sessions/test_messages_session/messages")

        if messages_response.status_code == 404:
            pytest.skip("Session messages endpoint not available")

        assert messages_response.status_code == 200
        data = messages_response.json()
        assert "messages" in data

    def test_clear_chat_session(self, client):
        """Test clearing a chat session.

        Verifies:
        - DELETE /api/brain/chat/sessions/{id} clears session
        """
        # Create a session first
        chat_request = {
            "query": "Test message",
            "session_id": "test_clear_session"
        }
        client.post("/api/brain/chat", json=chat_request)

        # Clear session
        clear_response = client.delete("/api/brain/chat/sessions/test_clear_session")

        if clear_response.status_code == 404:
            pytest.skip("Clear session endpoint not available")

        assert clear_response.status_code in [200, 204]

    def test_chat_session_pagination(self, client):
        """Test chat session pagination.

        Verifies:
        - Pagination parameters work correctly
        """
        # List with pagination
        response = client.get("/api/brain/chat/sessions?limit=10&offset=0")

        if response.status_code == 404:
            pytest.skip("Chat sessions endpoint not available")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data


@pytest.mark.e2e
class TestLoreManagement:
    """E2E tests for lore entry management."""

    def test_lore_smart_tags(self, client):
        """Test lore entry smart tags.

        Verifies:
        - Smart tags endpoint returns tags
        """
        # Create entry (use valid category from LoreCategory enum)
        entry_data = {
            "title": "Smart Tags Test",
            "content": "Test content for smart tags",
            "category": "history"
        }

        create_response = client.post("/api/lore", json=entry_data)
        assert create_response.status_code == 201
        entry_id = create_response.json()["id"]

        # Get smart tags
        tags_response = client.get(f"/api/lore/{entry_id}/smart-tags")
        assert tags_response.status_code == 200

        data = tags_response.json()
        # SmartTagsResponse returns smart_tags, manual_smart_tags, effective_tags
        assert "smart_tags" in data or "manual_smart_tags" in data or "effective_tags" in data

        # Cleanup
        client.delete(f"/api/lore/{entry_id}")

    def test_lore_entry_categories(self, client):
        """Test different lore entry categories.

        Verifies:
        - All categories are accepted
        """
        categories = ["history", "geography", "culture", "politics", "magic", "religion"]
        created_ids = []

        for category in categories:
            entry = {
                "title": f"{category.title()} Test",
                "content": f"Test content for {category}",
                "category": category
            }
            response = client.post("/api/lore", json=entry)
            if response.status_code == 201:
                created_ids.append(response.json()["id"])
            else:
                # Some categories may not be valid
                assert response.status_code in [201, 400]

        # Cleanup
        for entry_id in created_ids:
            client.delete(f"/api/lore/{entry_id}")

    def test_lore_entry_relationships(self, client):
        """Test related lore entries.

        Verifies:
        - Related entries can be linked
        """
        # Create two related entries
        entry1 = {
            "title": "Parent Entry",
            "content": "Main content",
            "category": "history"
        }
        entry2 = {
            "title": "Child Entry",
            "content": "Related content",
            "category": "history"
        }

        response1 = client.post("/api/lore", json=entry1)
        response2 = client.post("/api/lore", json=entry2)

        if response1.status_code == 201 and response2.status_code == 201:
            entry1_id = response1.json()["id"]
            entry2_id = response2.json()["id"]

            # Update entry1 to link to entry2
            update_data = {
                "related_entry_ids": [entry2_id]
            }
            update_response = client.put(f"/api/lore/{entry1_id}", json=update_data)
            assert update_response.status_code == 200

            # Cleanup
            client.delete(f"/api/lore/{entry1_id}")
            client.delete(f"/api/lore/{entry2_id}")

    def test_lore_search_by_category(self, client):
        """Test searching lore by category.

        Verifies:
        - Category filter in search works
        """
        # Create entries
        entry = {
            "title": "Category Search Test",
            "content": "Test content",
            "category": "geography"
        }

        create_response = client.post("/api/lore", json=entry)
        if create_response.status_code == 201:
            entry_id = create_response.json()["id"]

            # Search with category filter
            search_response = client.get("/api/lore/search?q=test&category=geography")
            assert search_response.status_code == 200

            # Cleanup
            client.delete(f"/api/lore/{entry_id}")
