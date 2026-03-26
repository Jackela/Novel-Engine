"""Integration tests for canonical knowledge routes."""

from __future__ import annotations

from src.apps.api.dependencies import get_jwt_manager


def _auth_headers(
    *,
    user_id: str = "user-knowledge-1",
    username: str = "knowledge-user",
    email: str = "knowledge@example.com",
) -> dict[str, str]:
    token = get_jwt_manager().create_access_token(
        user_id=user_id,
        username=username,
        email=email,
        roles=["user"],
    )
    return {"Authorization": f"Bearer {token}"}


def test_create_knowledge_base_requires_authentication(canonical_client) -> None:
    response = canonical_client.post(
        "/api/v1/knowledge/knowledge-bases",
        json={"name": "Private Knowledge Base"},
    )

    assert response.status_code == 401


def test_create_knowledge_base_uses_authenticated_owner(canonical_client) -> None:
    response = canonical_client.post(
        "/api/v1/knowledge/knowledge-bases",
        params={"owner_id": "attacker-controlled"},
        headers=_auth_headers(user_id="owner-123"),
        json={"name": "Owner Bound KB"},
    )

    assert response.status_code == 201
    assert response.json()["owner_id"] == "owner-123"


def test_global_search_aggregates_across_requested_knowledge_bases(
    canonical_client,
) -> None:
    headers = _auth_headers(user_id="search-owner")

    first_kb = canonical_client.post(
        "/api/v1/knowledge/knowledge-bases",
        headers=headers,
        json={"name": "First KB"},
    ).json()
    second_kb = canonical_client.post(
        "/api/v1/knowledge/knowledge-bases",
        headers=headers,
        json={"name": "Second KB"},
    ).json()

    first_doc = canonical_client.post(
        f"/api/v1/knowledge/knowledge-bases/{first_kb['id']}/documents",
        json={
            "title": "Moon Archive",
            "content": "Moon records and lunar history for the archive.",
            "tags": ["astronomy"],
        },
    ).json()
    second_doc = canonical_client.post(
        f"/api/v1/knowledge/knowledge-bases/{second_kb['id']}/documents",
        json={
            "title": "Moon Garden",
            "content": "Moon garden notes and lunar cultivation rituals.",
            "tags": ["botany"],
        },
    ).json()

    response = canonical_client.post(
        "/api/v1/knowledge/search",
        params=[
            ("knowledge_base_ids", first_kb["id"]),
            ("knowledge_base_ids", second_kb["id"]),
        ],
        json={"query": "moon", "top_k": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    result_ids = {result["document_id"] for result in payload["results"]}
    assert payload["total_results"] == 2
    assert result_ids == {first_doc["id"], second_doc["id"]}
