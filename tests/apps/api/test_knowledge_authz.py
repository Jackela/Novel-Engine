"""Knowledge-base authorization boundary tests."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _login_operator(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "email": "operator@novel.engine",
            "password": "demo-password",
        },
    )
    assert response.status_code == 200


def _login_writer(client: TestClient) -> None:
    register_response = client.post(
        "/api/auth/register",
        json={
            "email": "writer@example.com",
            "username": "writer",
            "password": "supersecret",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/api/auth/login",
        json={"username": "writer", "password": "supersecret"},
    )
    assert login_response.status_code == 200


def _create_knowledge_base(client: TestClient, *, is_public: bool) -> str:
    response = client.post(
        "/api/knowledge/knowledge-bases",
        json={
            "name": "Editorial Memory",
            "description": "Private source notes",
            "is_public": is_public,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _upload_document(client: TestClient, knowledge_base_id: str) -> str:
    response = client.post(
        f"/api/knowledge/knowledge-bases/{knowledge_base_id}/documents",
        json={
            "title": "Continuity Notes",
            "content": "The bridge promise must pay off before publication.",
            "tags": ["continuity"],
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def test_private_knowledge_base_write_and_read_require_owner(
    canonical_app: FastAPI,
) -> None:
    with (
        TestClient(canonical_app, raise_server_exceptions=False) as owner_client,
        TestClient(canonical_app, raise_server_exceptions=False) as other_client,
        TestClient(canonical_app, raise_server_exceptions=False) as anonymous_client,
    ):
        _login_operator(owner_client)
        knowledge_base_id = _create_knowledge_base(owner_client, is_public=False)
        document_id = _upload_document(owner_client, knowledge_base_id)

        _login_writer(other_client)

        private_document_path = (
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}"
            f"/documents/{document_id}"
        )
        assert anonymous_client.get(private_document_path).status_code == 404
        assert other_client.get(private_document_path).status_code == 404

        upload_path = (
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}/documents"
        )
        assert (
            anonymous_client.post(
                upload_path,
                json={
                    "title": "Anonymous write",
                    "content": "This should require authentication.",
                },
            ).status_code
            == 401
        )
        assert (
            other_client.post(
                upload_path,
                json={
                    "title": "Intrusion",
                    "content": "Cross-tenant writes must not land.",
                },
            ).status_code
            == 404
        )


def test_public_knowledge_base_is_read_only_for_non_owners(
    canonical_app: FastAPI,
) -> None:
    with (
        TestClient(canonical_app, raise_server_exceptions=False) as owner_client,
        TestClient(canonical_app, raise_server_exceptions=False) as other_client,
        TestClient(canonical_app, raise_server_exceptions=False) as anonymous_client,
    ):
        _login_operator(owner_client)
        knowledge_base_id = _create_knowledge_base(owner_client, is_public=True)
        document_id = _upload_document(owner_client, knowledge_base_id)

        list_response = anonymous_client.get(
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}/documents"
        )
        assert list_response.status_code == 200
        assert list_response.json()["total"] == 1

        document_response = anonymous_client.get(
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}"
            f"/documents/{document_id}"
        )
        assert document_response.status_code == 200

        stats_response = anonymous_client.get(
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}/stats"
        )
        assert stats_response.status_code == 200
        assert stats_response.json()["is_public"] is True

        search_response = anonymous_client.post(
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}/search",
            json={"query": "bridge promise", "top_k": 3},
        )
        assert search_response.status_code == 200

        _login_writer(other_client)
        delete_response = other_client.delete(
            f"/api/knowledge/knowledge-bases/{knowledge_base_id}"
            f"/documents/{document_id}"
        )
        assert delete_response.status_code == 404
