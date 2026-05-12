"""Check definitions for the public API audit."""

from __future__ import annotations

import time

from .assertions import (
    assert_contains,
    assert_json_keys,
    assert_status_field,
    assert_workspace_prefix,
)
from .executor import AuditRunner
from .models import AuditContext


def execute_checks(runner: AuditRunner) -> None:
    context = AuditContext(suffix=int(time.time()))
    run_platform_checks(runner)
    run_story_pre_auth_checks(runner)
    run_auth_and_guest_checks(runner, context)
    run_story_checks(runner, context)
    run_knowledge_checks(runner, context)


def run_platform_checks(runner: AuditRunner) -> None:
    runner.check(
        category="platform",
        name="Root metadata endpoint",
        method="GET",
        route_template="/",
        request_path="/",
        expected_statuses=[200],
        assertion=assert_json_keys("name", "version", "api_base"),
    )
    runner.check(
        category="platform",
        name="OpenAPI schema endpoint",
        method="GET",
        route_template="/openapi.json",
        request_path="/openapi.json",
        expected_statuses=[200],
        assertion=assert_json_keys("openapi", "paths"),
    )
    runner.check(
        category="platform",
        name="Swagger docs endpoint",
        method="GET",
        route_template="/docs",
        request_path="/docs",
        expected_statuses=[200],
        assertion=assert_contains("Swagger UI"),
    )
    runner.check(
        category="platform",
        name="ReDoc endpoint",
        method="GET",
        route_template="/redoc",
        request_path="/redoc",
        expected_statuses=[200],
        assertion=assert_contains("redoc"),
    )
    runner.check(
        category="platform",
        name="API versions endpoint",
        method="GET",
        route_template="/api/versions",
        request_path="/api/versions",
        expected_statuses=[200],
        assertion=assert_json_keys("current_version", "supported_versions", "versions"),
    )
    runner.check(
        category="platform",
        name="Health endpoint returns payload semantic status",
        method="GET",
        route_template="/health",
        request_path="/health",
        expected_statuses=[200],
        assertion=assert_json_keys("overall_status", "timestamp", "components"),
    )
    runner.check(
        category="platform",
        name="Liveness endpoint",
        method="GET",
        route_template="/health/live",
        request_path="/health/live",
        expected_statuses=[200],
        assertion=assert_status_field("alive"),
    )
    runner.check(
        category="platform",
        name="Readiness endpoint",
        method="GET",
        route_template="/health/ready",
        request_path="/health/ready",
        expected_statuses=[200, 503],
        assertion=assert_json_keys("status"),
    )
    runner.check(
        category="platform",
        name="Version endpoint",
        method="GET",
        route_template="/version",
        request_path="/version",
        expected_statuses=[200],
        assertion=assert_json_keys("version", "name", "environment"),
    )


def run_story_pre_auth_checks(runner: AuditRunner) -> None:
    runner.check(
        category="story",
        name="Create story without user/cookie author context fails",
        method="POST",
        route_template="/api/v1/story",
        request_path="/api/v1/story",
        expected_statuses=[400],
        request_kwargs={
            "json": {
                "title": "Missing Author Story",
                "genre": "fantasy",
                "premise": "A relay station collapses and the map has to be redrawn overnight.",
                "target_chapters": 3,
            }
        },
    )


def run_auth_and_guest_checks(runner: AuditRunner, context: AuditContext) -> None:
    runner.check(
        category="auth",
        name="Register user",
        method="POST",
        route_template="/api/v1/auth/register",
        request_path="/api/v1/auth/register",
        expected_statuses=[201],
        request_kwargs={
            "json": {
                "email": f"qa-operator-{context.suffix}@novel.engine",
                "username": f"qa_operator_{context.suffix}",
                "password": "demo-password",
            }
        },
        assertion=assert_json_keys("id", "username", "email", "roles"),
    )
    runner.check(
        category="auth",
        name="Register validation failure",
        method="POST",
        route_template="/api/v1/auth/register",
        request_path="/api/v1/auth/register",
        expected_statuses=[422],
        request_kwargs={
            "json": {
                "email": "bad-email",
                "username": "ab",
                "password": "short",
            }
        },
    )

    login_response = runner.check(
        category="auth",
        name="Login valid credentials",
        method="POST",
        route_template="/api/v1/auth/login",
        request_path="/api/v1/auth/login",
        expected_statuses=[200],
        request_kwargs={
            "json": {
                "email": "operator@novel.engine",
                "password": "demo-password",
            }
        },
        assertion=assert_json_keys("access_token", "refresh_token", "workspace_id", "user"),
    )
    runner.check(
        category="auth",
        name="Login invalid credentials",
        method="POST",
        route_template="/api/v1/auth/login",
        request_path="/api/v1/auth/login",
        expected_statuses=[401],
        request_kwargs={
            "json": {
                "email": "operator@novel.engine",
                "password": "wrong-password",
            }
        },
    )

    if login_response is not None and login_response.status_code == 200:
        login_payload = login_response.json()
        context.access_token = str(login_payload.get("access_token", ""))
        context.refresh_token = str(login_payload.get("refresh_token", ""))
        context.workspace_id = str(login_payload.get("workspace_id", ""))

    runner.check(
        category="auth",
        name="Get current user unauthorized",
        method="GET",
        route_template="/api/v1/auth/me",
        request_path="/api/v1/auth/me",
        expected_statuses=[401],
    )
    runner.check(
        category="auth",
        name="Get current user authorized",
        method="GET",
        route_template="/api/v1/auth/me",
        request_path="/api/v1/auth/me",
        expected_statuses=[200],
        request_kwargs={"headers": context.auth_headers},
        assertion=assert_json_keys("id", "username", "email", "roles"),
    )
    runner.check(
        category="auth",
        name="Refresh token valid",
        method="POST",
        route_template="/api/v1/auth/refresh",
        request_path="/api/v1/auth/refresh",
        expected_statuses=[200],
        request_kwargs={"json": {"refresh_token": context.refresh_token}},
        assertion=assert_json_keys("access_token", "token_type"),
    )
    runner.check(
        category="auth",
        name="Refresh token invalid",
        method="POST",
        route_template="/api/v1/auth/refresh",
        request_path="/api/v1/auth/refresh",
        expected_statuses=[401],
        request_kwargs={"json": {"refresh_token": "invalid-refresh-token"}},
    )
    runner.check(
        category="auth",
        name="Logout unauthorized",
        method="POST",
        route_template="/api/v1/auth/logout",
        request_path="/api/v1/auth/logout",
        expected_statuses=[401],
    )
    runner.check(
        category="auth",
        name="Logout authorized",
        method="POST",
        route_template="/api/v1/auth/logout",
        request_path="/api/v1/auth/logout",
        expected_statuses=[200],
        request_kwargs={"headers": context.auth_headers},
    )

    guest_response = runner.check(
        category="guest",
        name="Create guest session",
        method="POST",
        route_template="/api/v1/guest/session",
        request_path="/api/v1/guest/session",
        expected_statuses=[200],
        assertion=assert_workspace_prefix("guest-"),
    )
    if guest_response is not None and guest_response.status_code == 200:
        context.guest_workspace_id = str(guest_response.json().get("workspace_id", ""))

    runner.check(
        category="guest",
        name="Resume guest session with explicit workspace id",
        method="POST",
        route_template="/api/v1/guest/session",
        request_path="/api/v1/guest/session",
        expected_statuses=[200],
        request_kwargs={"json": {"workspace_id": context.guest_workspace_id}},
        assertion=assert_workspace_prefix("guest-"),
    )
    runner.check(
        category="guest",
        name="Reject non-guest workspace from guest endpoint",
        method="POST",
        route_template="/api/v1/guest/session",
        request_path="/api/v1/guest/session",
        expected_statuses=[200],
        request_kwargs={"json": {"workspace_id": "user-operator"}},
        assertion=assert_workspace_prefix("guest-"),
    )


def run_story_checks(runner: AuditRunner, context: AuditContext) -> None:
    story_payload = {
        "title": f"QA Story {context.suffix}",
        "genre": "fantasy",
        "premise": "A border courier finds an atlas that redraws city law each midnight.",
        "target_chapters": 3,
        "author_id": context.workspace_id or "user-operator",
        "themes": ["memory", "border law", "storm routes"],
        "tone": "commercial web fiction",
    }

    runner.check(
        category="story",
        name="List stories for author",
        method="GET",
        route_template="/api/v1/story",
        request_path=f"/api/v1/story?author_id={story_payload['author_id']}&limit=20&offset=0",
        expected_statuses=[200],
        assertion=assert_json_keys("stories", "count", "limit", "offset"),
    )
    create_story_response = runner.check(
        category="story",
        name="Create story",
        method="POST",
        route_template="/api/v1/story",
        request_path="/api/v1/story",
        expected_statuses=[200],
        request_kwargs={"json": story_payload},
        assertion=assert_json_keys("story", "workspace"),
    )

    if create_story_response is not None and create_story_response.status_code == 200:
        context.story_id = str(create_story_response.json()["story"]["id"])

    missing_story_id = "00000000-0000-0000-0000-000000000001"
    runner.check(
        category="story",
        name="Get unknown story returns 404",
        method="GET",
        route_template="/api/v1/story/{story_id}",
        request_path=f"/api/v1/story/{missing_story_id}",
        expected_statuses=[404],
    )

    runner.check(
        category="story",
        name="Get story by id",
        method="GET",
        route_template="/api/v1/story/{story_id}",
        request_path=f"/api/v1/story/{context.story_id}",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace"),
    )
    runner.check(
        category="story",
        name="Get story workspace",
        method="GET",
        route_template="/api/v1/story/{story_id}/workspace",
        request_path=f"/api/v1/story/{context.story_id}/workspace",
        expected_statuses=[200],
        assertion=assert_json_keys("workspace"),
    )
    runner.check(
        category="story",
        name="Generate blueprint",
        method="POST",
        route_template="/api/v1/story/{story_id}/blueprint",
        request_path=f"/api/v1/story/{context.story_id}/blueprint",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace", "blueprint"),
    )
    runner.check(
        category="story",
        name="Generate outline",
        method="POST",
        route_template="/api/v1/story/{story_id}/outline",
        request_path=f"/api/v1/story/{context.story_id}/outline",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace", "outline"),
    )
    runner.check(
        category="story",
        name="Draft validation failure for invalid chapter count",
        method="POST",
        route_template="/api/v1/story/{story_id}/draft",
        request_path=f"/api/v1/story/{context.story_id}/draft",
        expected_statuses=[422],
        request_kwargs={"json": {"target_chapters": 0}},
    )
    runner.check(
        category="story",
        name="Draft story chapters",
        method="POST",
        route_template="/api/v1/story/{story_id}/draft",
        request_path=f"/api/v1/story/{context.story_id}/draft",
        expected_statuses=[200],
        request_kwargs={"json": {"target_chapters": 3}},
        assertion=assert_json_keys("story", "workspace", "drafted_chapters"),
    )
    runner.check(
        category="story",
        name="Review story",
        method="POST",
        route_template="/api/v1/story/{story_id}/review",
        request_path=f"/api/v1/story/{context.story_id}/review",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace", "report"),
    )
    runner.check(
        category="story",
        name="Revise story",
        method="POST",
        route_template="/api/v1/story/{story_id}/revise",
        request_path=f"/api/v1/story/{context.story_id}/revise",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace", "report", "revision_notes"),
    )
    runner.check(
        category="story",
        name="Export story",
        method="POST",
        route_template="/api/v1/story/{story_id}/export",
        request_path=f"/api/v1/story/{context.story_id}/export",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace", "export"),
    )
    runner.check(
        category="story",
        name="Publish story",
        method="POST",
        route_template="/api/v1/story/{story_id}/publish",
        request_path=f"/api/v1/story/{context.story_id}/publish",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "workspace", "report"),
    )
    runner.check(
        category="story",
        name="Get story runs",
        method="GET",
        route_template="/api/v1/story/{story_id}/runs",
        request_path=f"/api/v1/story/{context.story_id}/runs",
        expected_statuses=[200],
        assertion=assert_json_keys("current_run", "runs"),
    )
    runner.check(
        category="story",
        name="Get story artifacts",
        method="GET",
        route_template="/api/v1/story/{story_id}/artifacts",
        request_path=f"/api/v1/story/{context.story_id}/artifacts",
        expected_statuses=[200],
        assertion=assert_json_keys("current", "history"),
    )
    create_run_response = runner.check(
        category="story",
        name="Create story run resource",
        method="POST",
        route_template="/api/v1/story/{story_id}/runs",
        request_path=f"/api/v1/story/{context.story_id}/runs",
        expected_statuses=[200],
        request_kwargs={
            "json": {
                "operation": "pipeline",
                "target_chapters": 3,
                "publish": False,
            }
        },
        assertion=assert_json_keys("run", "events", "artifacts", "latest_snapshot"),
    )

    if create_run_response is not None and create_run_response.status_code == 200:
        context.run_id = str(create_run_response.json()["run"]["run_id"])

    runner.check(
        category="story",
        name="Get story run detail",
        method="GET",
        route_template="/api/v1/story/{story_id}/runs/{run_id}",
        request_path=f"/api/v1/story/{context.story_id}/runs/{context.run_id}",
        expected_statuses=[200],
        assertion=assert_json_keys("run", "events", "artifacts", "latest_snapshot"),
    )
    runner.check(
        category="story",
        name="Run full pipeline endpoint",
        method="POST",
        route_template="/api/v1/story/pipeline",
        request_path="/api/v1/story/pipeline",
        expected_statuses=[200],
        request_kwargs={
            "json": {
                "title": f"QA Pipeline Story {context.suffix}",
                "genre": "mystery",
                "premise": (
                    "A flood-gate tribunal archives every oath before dawn and one ledger is forged."
                ),
                "target_chapters": 3,
                "author_id": story_payload["author_id"],
                "publish": True,
            }
        },
        assertion=assert_json_keys("story", "workspace", "published"),
    )


def run_knowledge_checks(runner: AuditRunner, context: AuditContext) -> None:
    runner.check(
        category="knowledge",
        name="Create knowledge base unauthorized",
        method="POST",
        route_template="/api/v1/knowledge/knowledge-bases",
        request_path="/api/v1/knowledge/knowledge-bases",
        expected_statuses=[401],
        request_kwargs={"json": {"name": "Unauthorized KB"}},
    )
    create_kb_response = runner.check(
        category="knowledge",
        name="Create knowledge base",
        method="POST",
        route_template="/api/v1/knowledge/knowledge-bases",
        request_path="/api/v1/knowledge/knowledge-bases",
        expected_statuses=[201],
        request_kwargs={
            "headers": context.auth_headers,
            "json": {
                "name": f"QA Knowledge Base {context.suffix}",
                "description": "Public API audit corpus",
                "project_id": "qa-audit",
                "is_public": False,
            },
        },
        assertion=assert_json_keys(
            "id",
            "name",
            "owner_id",
            "document_count",
            "indexed_count",
            "created_at",
            "updated_at",
        ),
    )

    if create_kb_response is not None and create_kb_response.status_code == 201:
        context.knowledge_base_id = str(create_kb_response.json()["id"])

    runner.check(
        category="knowledge",
        name="List knowledge documents",
        method="GET",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/documents",
        request_path=(
            "/api/v1/knowledge/knowledge-bases/"
            f"{context.knowledge_base_id}/documents?limit=100&offset=0"
        ),
        expected_statuses=[200],
        assertion=assert_json_keys("documents", "total"),
    )
    upload_doc_response = runner.check(
        category="knowledge",
        name="Upload knowledge document",
        method="POST",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/documents",
        request_path=(
            f"/api/v1/knowledge/knowledge-bases/{context.knowledge_base_id}/documents"
        ),
        expected_statuses=[201],
        request_kwargs={
            "json": {
                "title": "Audit Document",
                "content": "This document is used to validate semantic and global search behavior.",
                "content_type": "text",
                "source": "qa-audit",
                "tags": ["audit", "smoke"],
            }
        },
        assertion=assert_json_keys("id", "title", "content", "is_indexed", "metadata"),
    )

    if upload_doc_response is not None and upload_doc_response.status_code == 201:
        context.document_id = str(upload_doc_response.json()["id"])

    runner.check(
        category="knowledge",
        name="Get knowledge document",
        method="GET",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
        request_path=(
            f"/api/v1/knowledge/knowledge-bases/{context.knowledge_base_id}/documents/{context.document_id}"
        ),
        expected_statuses=[200],
        assertion=assert_json_keys("id", "knowledge_base_id", "title", "content"),
    )
    runner.check(
        category="knowledge",
        name="Index knowledge document",
        method="POST",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}/index",
        request_path=(
            "/api/v1/knowledge/knowledge-bases/"
            f"{context.knowledge_base_id}/documents/{context.document_id}/index"
        ),
        expected_statuses=[200],
        assertion=assert_json_keys("id", "is_indexed"),
    )
    runner.check(
        category="knowledge",
        name="Semantic search within knowledge base",
        method="POST",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/search",
        request_path=f"/api/v1/knowledge/knowledge-bases/{context.knowledge_base_id}/search",
        expected_statuses=[200],
        request_kwargs={"json": {"query": "semantic search behavior", "top_k": 5}},
        assertion=assert_json_keys("query", "results", "total_results"),
    )
    runner.check(
        category="knowledge",
        name="Global search requires knowledge_base_ids",
        method="POST",
        route_template="/api/v1/knowledge/search",
        request_path="/api/v1/knowledge/search",
        expected_statuses=[400],
        request_kwargs={"json": {"query": "missing ids", "top_k": 3}},
    )
    runner.check(
        category="knowledge",
        name="Global search across selected bases",
        method="POST",
        route_template="/api/v1/knowledge/search",
        request_path=f"/api/v1/knowledge/search?knowledge_base_ids={context.knowledge_base_id}",
        expected_statuses=[200],
        request_kwargs={"json": {"query": "semantic search behavior", "top_k": 3}},
        assertion=assert_json_keys("query", "results", "total_results"),
    )
    runner.check(
        category="knowledge",
        name="Get knowledge base stats",
        method="GET",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/stats",
        request_path=f"/api/v1/knowledge/knowledge-bases/{context.knowledge_base_id}/stats",
        expected_statuses=[200],
    )
    runner.check(
        category="knowledge",
        name="Delete knowledge document",
        method="DELETE",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
        request_path=(
            f"/api/v1/knowledge/knowledge-bases/{context.knowledge_base_id}/documents/{context.document_id}"
        ),
        expected_statuses=[204],
    )
    runner.check(
        category="knowledge",
        name="Deleted knowledge document returns 404",
        method="GET",
        route_template="/api/v1/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
        request_path=(
            f"/api/v1/knowledge/knowledge-bases/{context.knowledge_base_id}/documents/{context.document_id}"
        ),
        expected_statuses=[404],
    )
