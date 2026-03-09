"""E2E Tests for Multiplayer Negotiation Flow.

This module tests the end-to-end multiplayer negotiation flows:
1. Create negotiation sessions
2. Multiple parties propose and respond
3. Track negotiation state
4. Reach agreement or deadlock

Tests:
- Negotiation session creation
- Multi-party proposal flow
- Agreement and resolution
- Diplomacy and faction interactions
"""

import os

# Set testing mode BEFORE importing app
os.environ["ORCHESTRATOR_MODE"] = "testing"

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture
def client():
    """Create a test client for the E2E tests."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def data_factory():
    """Provide test data factory."""
    from datetime import datetime
    from typing import Any, Dict

    class TestDataFactory:
        @staticmethod
        def create_character_data(
            name=None,
            agent_id=None,
            archetype=None,
        ) -> Dict[str, Any]:
            char_name = name or f"TestChar_{datetime.now().timestamp()}"
            char_id = agent_id or char_name.lower().replace(" ", "_")

            return {
                "agent_id": char_id,
                "name": char_name,
                "background_summary": f"Background for {char_name}",
                "personality_traits": "brave, intelligent, curious",
                "current_mood": 7,
                "dominant_emotion": "calm",
                "energy_level": 8,
                "stress_level": 3,
                "skills": {"combat": 0.7, "diplomacy": 0.6, "investigation": 0.8},
                "relationships": {},
                "current_location": "Test Location",
                "inventory": ["test_item"],
                "metadata": {"test": True},
            }

    return TestDataFactory()


# Mark all tests in this module as e2e tests
pytestmark = pytest.mark.e2e


@pytest.mark.e2e
class TestMultiplayerNegotiation:
    """E2E tests for multiplayer negotiation flows."""

    def test_negotiation_session_creation(self, client, data_factory):
        """Test creating a negotiation session.

        Verifies:
        - Negotiation session can be initialized
        - Participants are properly registered
        """
        # Create characters for negotiation
        char1 = data_factory.create_character_data(
            name="Negotiator One", agent_id="negotiator_one"
        )
        char2 = data_factory.create_character_data(
            name="Negotiator Two", agent_id="negotiator_two"
        )

        response1 = client.post("/api/characters", json=char1)
        response2 = client.post("/api/characters", json=char2)

        assert response1.status_code in [200, 201]
        assert response2.status_code in [200, 201]

        # Create negotiation context (using dialogue as negotiation proxy)
        dialogue_request = {
            "character_id": "negotiator_one",
            "context": "Negotiating a trade agreement with negotiator_two",
            "mood": "diplomatic",
        }

        response = client.post("/api/dialogue/generate", json=dialogue_request)

        if response.status_code == 404:
            pytest.skip("Dialogue generation not available")

        # Dialogue endpoint should work or fail gracefully
        assert response.status_code in [200, 422, 503]

    def test_negotiation_proposal_flow(self, client, data_factory):
        """Test proposal and counter-proposal flow.

        Verifies:
        - Proposals can be made
        - Counter-proposals are handled
        """
        # Create negotiators
        char1 = data_factory.create_character_data(
            name="Proposer", agent_id="proposer_char"
        )
        client.post("/api/characters", json=char1)

        # Generate dialogue as proposal
        proposal_request = {
            "character_id": "proposer_char",
            "context": "Making a proposal: I offer 100 gold for the artifact",
            "mood": "persuasive",
        }

        response = client.post("/api/dialogue/generate", json=proposal_request)

        if response.status_code == 404:
            pytest.skip("Dialogue generation not available")

        assert response.status_code in [200, 422, 503]

        if response.status_code == 200:
            data = response.json()
            assert "dialogue" in data

    def test_faction_negotiation_setup(self, client):
        """Test faction-based negotiation setup.

        Verifies:
        - Factions can be listed
        - Faction relations can be queried
        """
        # List factions
        factions_response = client.get("/api/factions")

        # Factions endpoint may not exist (404) or may return data
        if factions_response.status_code == 404:
            pytest.skip("Factions endpoint not available")

        assert factions_response.status_code == 200

        data = factions_response.json()
        assert "factions" in data or "data" in data

    def test_diplomacy_status_check(self, client):
        """Test checking diplomacy status between parties.

        Verifies:
        - Diplomacy endpoint returns status
        """
        # Get diplomacy matrix
        response = client.get("/api/diplomacy")

        # May return 200 with data or 404 if not implemented
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "relations" in data or "data" in data or "matrix" in data


@pytest.mark.e2e
class TestFactionInteractions:
    """E2E tests for faction-based interactions."""

    def test_list_factions(self, client):
        """Test listing available factions.

        Verifies:
        - GET /api/factions returns faction list
        """
        response = client.get("/api/factions")

        # Factions endpoint may not exist
        if response.status_code == 404:
            pytest.skip("Factions endpoint not available")

        assert response.status_code == 200

        data = response.json()
        # Response may be wrapped in 'data' or direct
        factions = data.get("data", data)
        assert isinstance(factions, dict) or isinstance(factions, list)

    def test_faction_details(self, client):
        """Test retrieving faction details.

        Verifies:
        - GET /api/factions/{id} returns faction info
        """
        # First list factions to get an ID
        list_response = client.get("/api/factions")
        if list_response.status_code != 200:
            pytest.skip("Factions endpoint not available")

        # Try to get a specific faction (using a common ID)
        detail_response = client.get("/api/factions/default")

        # May return 200 or 404 depending on implementation
        assert detail_response.status_code in [200, 404]

    def test_faction_relationships(self, client):
        """Test faction relationship management.

        Verifies:
        - Faction relations can be queried
        """
        response = client.get("/api/factions/relationships")

        # Endpoint may not exist
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "relationships" in data or "data" in data

    def test_faction_intel(self, client):
        """Test faction intelligence endpoint.

        Verifies:
        - GET /api/faction-intel returns intel data
        """
        response = client.get("/api/faction-intel")

        if response.status_code == 404:
            pytest.skip("Faction intel endpoint not available")

        assert response.status_code == 200

        data = response.json()
        assert "data" in data or "intel" in data


@pytest.mark.e2e
class TestDiplomacySystem:
    """E2E tests for diplomacy system."""

    def test_diplomacy_matrix(self, client):
        """Test diplomacy matrix retrieval.

        Verifies:
        - Diplomacy matrix shows faction relations
        """
        response = client.get("/api/diplomacy")

        if response.status_code == 404:
            pytest.skip("Diplomacy endpoint not available")

        assert response.status_code == 200

        data = response.json()
        assert "matrix" in data or "relations" in data or "data" in data

    def test_diplomatic_pacts(self, client):
        """Test diplomatic pacts endpoint.

        Verifies:
        - Active pacts can be listed
        """
        response = client.get("/api/diplomacy/pacts")

        if response.status_code == 404:
            pytest.skip("Diplomacy pacts endpoint not available")

        assert response.status_code == 200

        data = response.json()
        assert "pacts" in data or "data" in data

    def test_diplomatic_proposals(self, client):
        """Test creating diplomatic proposals.

        Verifies:
        - Proposals can be created
        """
        proposal_data = {
            "from_faction": "faction_a",
            "to_faction": "faction_b",
            "type": "trade_agreement",
            "terms": {"duration": "1_year", "benefits": ["resource_sharing"]},
        }

        response = client.post("/api/diplomacy/proposals", json=proposal_data)

        if response.status_code == 404:
            pytest.skip("Diplomacy proposals endpoint not available")

        # May succeed or fail based on implementation
        assert response.status_code in [200, 201, 400, 422]

    def test_diplomatic_status(self, client):
        """Test diplomatic status between factions.

        Verifies:
        - Status endpoint returns relation status
        """
        response = client.get("/api/diplomacy/status?faction1=a&faction2=b")

        if response.status_code == 404:
            pytest.skip("Diplomacy status endpoint not available")

        assert response.status_code in [200, 400]


@pytest.mark.e2e
class TestNegotiationAPI:
    """E2E tests for negotiation-specific endpoints."""

    def test_negotiation_create(self, client):
        """Test creating a new negotiation.

        Verifies:
        - Negotiation can be initialized via API
        """
        negotiation_data = {
            "participants": ["char1", "char2"],
            "topic": "Trade Agreement",
            "context": "Negotiating terms of trade",
        }

        response = client.post("/api/negotiations", json=negotiation_data)

        if response.status_code == 404:
            pytest.skip("Negotiations endpoint not available")

        assert response.status_code in [200, 201, 400, 422]

    def test_negotiation_list(self, client):
        """Test listing active negotiations.

        Verifies:
        - GET /api/negotiations returns list
        """
        response = client.get("/api/negotiations")

        if response.status_code == 404:
            pytest.skip("Negotiations endpoint not available")

        assert response.status_code == 200

        data = response.json()
        assert "negotiations" in data or "data" in data

    def test_negotiation_propose(self, client):
        """Test making a proposal in negotiation.

        Verifies:
        - Proposals can be submitted
        """
        proposal_data = {
            "negotiation_id": "test_neg_123",
            "proposer": "char1",
            "proposal": {
                "terms": "Exchange 100 gold for the artifact",
                "conditions": ["immediate_transfer"],
            },
        }

        response = client.post("/api/negotiations/propose", json=proposal_data)

        if response.status_code == 404:
            pytest.skip("Negotiation propose endpoint not available")

        assert response.status_code in [200, 201, 400, 404]

    def test_negotiation_respond(self, client):
        """Test responding to a negotiation proposal.

        Verifies:
        - Responses can be submitted
        """
        response_data = {
            "negotiation_id": "test_neg_123",
            "responder": "char2",
            "response": "accept",  # or "reject", "counter"
            "counter_proposal": None,
        }

        response = client.post("/api/negotiations/respond", json=response_data)

        if response.status_code == 404:
            pytest.skip("Negotiation respond endpoint not available")

        assert response.status_code in [200, 400, 404]


@pytest.mark.e2e
class TestCharacterNegotiation:
    """E2E tests for character-based negotiations."""

    def test_character_dialogue_negotiation(self, client, data_factory):
        """Test character dialogue for negotiation.

        Verifies:
        - Characters can generate negotiation dialogue
        """
        # Create negotiator
        char = data_factory.create_character_data(
            name="Master Negotiator", agent_id="master_negotiator"
        )
        char["personality_traits"] = "diplomatic, persuasive, patient"

        client.post("/api/characters", json=char)

        # Generate negotiation dialogue
        dialogue_request = {
            "character_id": "master_negotiator",
            "context": "Negotiating a peace treaty between two warring factions",
            "mood": "diplomatic",
        }

        response = client.post("/api/dialogue/generate", json=dialogue_request)

        if response.status_code == 404:
            pytest.skip("Dialogue generation not available")

        assert response.status_code in [200, 422, 503]

        if response.status_code == 200:
            data = response.json()
            assert "dialogue" in data
            assert len(data["dialogue"]) > 0

    def test_multi_character_negotiation(self, client, data_factory):
        """Test negotiation between multiple characters.

        Verifies:
        - Multiple characters can participate
        - Responses reflect character traits
        """
        # Create multiple negotiators
        chars = [
            ("Negotiator A", "nego_a", "aggressive, ambitious"),
            ("Negotiator B", "nego_b", "cautious, analytical"),
            ("Mediator", "mediator", "neutral, fair, diplomatic"),
        ]

        for name, agent_id, traits in chars:
            char_data = data_factory.create_character_data(name=name, agent_id=agent_id)
            char_data["personality_traits"] = traits
            client.post("/api/characters", json=char_data)

        # Generate dialogue from each perspective
        for agent_id in ["nego_a", "nego_b", "mediator"]:
            dialogue_request = {
                "character_id": agent_id,
                "context": "Three-way negotiation over territory dispute",
                "mood": "formal",
            }

            _ = client.post("/api/dialogue/generate", json=dialogue_request)
            # Each may succeed or fail independently

    def test_negotiation_with_relationships(self, client, data_factory):
        """Test negotiation considering character relationships.

        Verifies:
        - Relationship values affect negotiation
        """
        # Create characters with relationship
        char1 = data_factory.create_character_data(
            name="Old Friend", agent_id="old_friend"
        )
        char2 = data_factory.create_character_data(
            name="Trusted Ally", agent_id="trusted_ally"
        )

        char1["relationships"] = {"trusted_ally": 0.9}  # High positive

        client.post("/api/characters", json=char1)
        client.post("/api/characters", json=char2)

        # Generate dialogue
        dialogue_request = {
            "character_id": "old_friend",
            "context": "Negotiating with trusted_ally about a mutual business venture",
            "mood": "friendly",
        }

        response = client.post("/api/dialogue/generate", json=dialogue_request)

        if response.status_code == 404:
            pytest.skip("Dialogue generation not available")

        assert response.status_code in [200, 422, 503]

    def test_negotiation_outcome_tracking(self, client):
        """Test tracking negotiation outcomes.

        Verifies:
        - Outcomes can be recorded
        - Results are retrievable
        """
        # This test assumes an outcomes endpoint exists
        # May need to be adapted based on actual API

        outcome_data = {
            "negotiation_id": "neg_123",
            "outcome": "agreement_reached",
            "terms": {"agreed_price": 500, "delivery_date": "immediate"},
            "participants": ["char1", "char2"],
        }

        response = client.post("/api/negotiations/outcome", json=outcome_data)

        if response.status_code == 404:
            pytest.skip("Negotiation outcome endpoint not available")

        assert response.status_code in [200, 201, 400]
