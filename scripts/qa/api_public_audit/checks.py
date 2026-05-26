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

TERMINAL_JOB_STATUSES = {"completed", "failed", "interrupted"}


def execute_checks(runner: AuditRunner) -> None:
    context = AuditContext(suffix=int(time.time()))
    run_platform_checks(runner)
    run_workspace_pre_auth_checks(runner)
    run_knowledge_pre_auth_checks(runner)
    run_auth_and_guest_checks(runner, context)
    run_workspace_checks(runner, context)
    run_knowledge_checks(runner, context)
    run_logout_checks(runner)


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


def run_workspace_pre_auth_checks(runner: AuditRunner) -> None:
    runner.check(
        category="workspaces",
        name="Create workspace without user/cookie principal fails",
        method="POST",
        route_template="/api/workspaces",
        request_path="/api/workspaces",
        expected_statuses=[401],
        request_kwargs={
            "json": {
                "workspace_id": "missing-principal",
                "title": "Missing Principal Story",
                "genre": "fantasy",
                "premise": "A relay station collapses and the map has to be redrawn overnight.",
                "target_chapters": 3,
            }
        },
    )


def run_knowledge_pre_auth_checks(runner: AuditRunner) -> None:
    runner.check(
        category="knowledge",
        name="Create knowledge base unauthorized",
        method="POST",
        route_template="/api/knowledge/knowledge-bases",
        request_path="/api/knowledge/knowledge-bases",
        expected_statuses=[401],
        request_kwargs={"json": {"name": "Unauthorized KB"}},
    )


def _poll_workspace_job(
    runner: AuditRunner,
    *,
    workspace_id: str,
    job_id: str,
    name: str,
    max_attempts: int = 20,
) -> None:
    if not job_id:
        runner.check(
            category="workspaces",
            name=f"{name} missing job id",
            method="GET",
            route_template="/api/workspaces/{workspace_id}/jobs/{job_id}",
            request_path=f"/api/workspaces/{workspace_id}/jobs/missing-job-id",
            expected_statuses=[404],
        )
        return

    request_path = f"/api/workspaces/{workspace_id}/jobs/{job_id}"
    for attempt in range(1, max_attempts + 1):
        response = runner.check(
            category="workspaces",
            name=f"{name} poll {attempt}",
            method="GET",
            route_template="/api/workspaces/{workspace_id}/jobs/{job_id}",
            request_path=request_path,
            expected_statuses=[200],
            assertion=assert_json_keys("job_id", "status", "result"),
        )
        if response is None or response.status_code != 200:
            return
        status_value = str(response.json().get("status", ""))
        if status_value in TERMINAL_JOB_STATUSES:
            break
        time.sleep(0.05)

    runner.check(
        category="workspaces",
        name=f"{name} completed",
        method="GET",
        route_template="/api/workspaces/{workspace_id}/jobs/{job_id}",
        request_path=request_path,
        expected_statuses=[200],
        assertion=assert_status_field("completed"),
    )


def run_auth_and_guest_checks(runner: AuditRunner, context: AuditContext) -> None:
    runner.check(
        category="auth",
        name="Register user",
        method="POST",
        route_template="/api/auth/register",
        request_path="/api/auth/register",
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
        route_template="/api/auth/register",
        request_path="/api/auth/register",
        expected_statuses=[422],
        request_kwargs={
            "json": {
                "email": "bad-email",
                "username": "ab",
                "password": "short",
            }
        },
    )
    runner.check(
        category="auth",
        name="Get current user unauthorized",
        method="GET",
        route_template="/api/auth/me",
        request_path="/api/auth/me",
        expected_statuses=[401],
    )

    login_response = runner.check(
        category="auth",
        name="Login valid credentials",
        method="POST",
        route_template="/api/auth/login",
        request_path="/api/auth/login",
        expected_statuses=[200],
        request_kwargs={
            "json": {
                "email": "operator@novel.engine",
                "password": "demo-password",
            }
        },
        assertion=assert_json_keys("workspace_id", "user", "active_workspace"),
    )
    runner.check(
        category="auth",
        name="Login invalid credentials",
        method="POST",
        route_template="/api/auth/login",
        request_path="/api/auth/login",
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
        context.workspace_id = str(login_payload.get("workspace_id", ""))

    runner.check(
        category="auth",
        name="Get current user authorized",
        method="GET",
        route_template="/api/auth/me",
        request_path="/api/auth/me",
        expected_statuses=[200],
        assertion=assert_json_keys("id", "username", "email", "roles"),
    )
    runner.check(
        category="auth",
        name="Refresh token valid",
        method="POST",
        route_template="/api/auth/refresh",
        request_path="/api/auth/refresh",
        expected_statuses=[200],
        request_kwargs={"json": {}},
        assertion=assert_json_keys("workspace_id", "user", "active_workspace"),
    )
    runner.check(
        category="auth",
        name="Refresh token invalid",
        method="POST",
        route_template="/api/auth/refresh",
        request_path="/api/auth/refresh",
        expected_statuses=[401],
        request_kwargs={"json": {"refresh_token": "invalid-refresh-token"}},
    )

    guest_response = runner.check(
        category="guest",
        name="Create guest session",
        method="POST",
        route_template="/api/guest/session",
        request_path="/api/guest/session",
        expected_statuses=[200],
        assertion=assert_workspace_prefix("guest-"),
    )
    if guest_response is not None and guest_response.status_code == 200:
        context.guest_workspace_id = str(guest_response.json().get("workspace_id", ""))

    runner.check(
        category="guest",
        name="Resume guest session with explicit workspace id",
        method="POST",
        route_template="/api/guest/session",
        request_path="/api/guest/session",
        expected_statuses=[200],
        request_kwargs={"json": {"workspace_id": context.guest_workspace_id}},
        assertion=assert_workspace_prefix("guest-"),
    )
    runner.check(
        category="guest",
        name="Reject non-guest workspace from guest endpoint",
        method="POST",
        route_template="/api/guest/session",
        request_path="/api/guest/session",
        expected_statuses=[200],
        request_kwargs={"json": {"workspace_id": "user-operator"}},
        assertion=assert_workspace_prefix("guest-"),
    )


def run_workspace_checks(runner: AuditRunner, context: AuditContext) -> None:
    workspace_id = f"qa-workspace-{context.suffix}"
    context.workspace_id = workspace_id
    runner.check(
        category="providers",
        name="List providers",
        method="GET",
        route_template="/api/providers",
        request_path="/api/providers",
        expected_statuses=[200],
        assertion=assert_json_keys("default_provider", "providers"),
    )
    runner.check(
        category="workspaces",
        name="Create local workspace",
        method="POST",
        route_template="/api/workspaces",
        request_path="/api/workspaces",
        expected_statuses=[201],
        request_kwargs={
            "json": {
                "workspace_id": workspace_id,
                "title": f"QA Story {context.suffix}",
                "genre": "mystery",
                "premise": (
                    "A flood-gate tribunal archives every oath before dawn and one ledger is forged."
                ),
                "target_chapters": 3,
            }
        },
        assertion=assert_json_keys("workspace_id", "story", "chapters", "runs"),
    )
    runner.check(
        category="workspaces",
        name="List local workspaces",
        method="GET",
        route_template="/api/workspaces",
        request_path="/api/workspaces",
        expected_statuses=[200],
        assertion=assert_json_keys("workspaces"),
    )
    job_response = runner.check(
        category="workspaces",
        name="Run workspace job",
        method="POST",
        route_template="/api/workspaces/{workspace_id}/jobs",
        request_path=f"/api/workspaces/{workspace_id}/jobs",
        expected_statuses=[202],
        request_kwargs={
            "json": {
                "operation": "run",
                "target_chapters": 3,
                "provider": "mock",
            }
        },
        assertion=assert_json_keys("job_id", "workspace_id", "operation", "status"),
    )
    job_id = ""
    if job_response is not None and job_response.status_code == 202:
        job_id = str(job_response.json().get("job_id", ""))
        context.job_id = job_id
    _poll_workspace_job(
        runner,
        workspace_id=workspace_id,
        job_id=job_id,
        name="Run workspace job",
    )
    runner.check(
        category="workspaces",
        name="Get workspace status",
        method="GET",
        route_template="/api/workspaces/{workspace_id}",
        request_path=f"/api/workspaces/{workspace_id}",
        expected_statuses=[200],
        assertion=assert_json_keys("story", "chapters", "latest_review", "runs", "jobs"),
    )
    review_job_response = runner.check(
        category="workspaces",
        name="Review workspace job",
        method="POST",
        route_template="/api/workspaces/{workspace_id}/jobs",
        request_path=f"/api/workspaces/{workspace_id}/jobs",
        expected_statuses=[202],
        request_kwargs={"json": {"operation": "review"}},
        assertion=assert_json_keys("job_id", "status"),
    )
    review_job_id = ""
    if review_job_response is not None and review_job_response.status_code == 202:
        review_job_id = str(review_job_response.json().get("job_id", ""))
    _poll_workspace_job(
        runner,
        workspace_id=workspace_id,
        job_id=review_job_id,
        name="Review workspace job",
    )
    export_job_response = runner.check(
        category="workspaces",
        name="Export workspace job",
        method="POST",
        route_template="/api/workspaces/{workspace_id}/jobs",
        request_path=f"/api/workspaces/{workspace_id}/jobs",
        expected_statuses=[202],
        request_kwargs={"json": {"operation": "export"}},
        assertion=assert_json_keys("job_id", "status"),
    )
    export_job_id = ""
    if export_job_response is not None and export_job_response.status_code == 202:
        export_job_id = str(export_job_response.json().get("job_id", ""))
    _poll_workspace_job(
        runner,
        workspace_id=workspace_id,
        job_id=export_job_id,
        name="Export workspace job",
    )


def run_knowledge_checks(runner: AuditRunner, context: AuditContext) -> None:
    create_kb_response = runner.check(
        category="knowledge",
        name="Create knowledge base",
        method="POST",
        route_template="/api/knowledge/knowledge-bases",
        request_path="/api/knowledge/knowledge-bases",
        expected_statuses=[201],
        request_kwargs={
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
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/documents",
        request_path=(
            "/api/knowledge/knowledge-bases/"
            f"{context.knowledge_base_id}/documents?limit=100&offset=0"
        ),
        expected_statuses=[200],
        assertion=assert_json_keys("documents", "total"),
    )
    upload_doc_response = runner.check(
        category="knowledge",
        name="Upload knowledge document",
        method="POST",
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/documents",
        request_path=(
            f"/api/knowledge/knowledge-bases/{context.knowledge_base_id}/documents"
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
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
        request_path=(
            f"/api/knowledge/knowledge-bases/{context.knowledge_base_id}/documents/{context.document_id}"
        ),
        expected_statuses=[200],
        assertion=assert_json_keys("id", "knowledge_base_id", "title", "content"),
    )
    runner.check(
        category="knowledge",
        name="Index knowledge document",
        method="POST",
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}/index",
        request_path=(
            "/api/knowledge/knowledge-bases/"
            f"{context.knowledge_base_id}/documents/{context.document_id}/index"
        ),
        expected_statuses=[200],
        assertion=assert_json_keys("id", "is_indexed"),
    )
    runner.check(
        category="knowledge",
        name="Semantic search within knowledge base",
        method="POST",
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/search",
        request_path=f"/api/knowledge/knowledge-bases/{context.knowledge_base_id}/search",
        expected_statuses=[200],
        request_kwargs={"json": {"query": "semantic search behavior", "top_k": 5}},
        assertion=assert_json_keys("query", "results", "total_results"),
    )
    runner.check(
        category="knowledge",
        name="Global search requires knowledge_base_ids",
        method="POST",
        route_template="/api/knowledge/search",
        request_path="/api/knowledge/search",
        expected_statuses=[400],
        request_kwargs={"json": {"query": "missing ids", "top_k": 3}},
    )
    runner.check(
        category="knowledge",
        name="Global search across selected bases",
        method="POST",
        route_template="/api/knowledge/search",
        request_path=f"/api/knowledge/search?knowledge_base_ids={context.knowledge_base_id}",
        expected_statuses=[200],
        request_kwargs={"json": {"query": "semantic search behavior", "top_k": 3}},
        assertion=assert_json_keys("query", "results", "total_results"),
    )
    runner.check(
        category="knowledge",
        name="Get knowledge base stats",
        method="GET",
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/stats",
        request_path=f"/api/knowledge/knowledge-bases/{context.knowledge_base_id}/stats",
        expected_statuses=[200],
    )
    runner.check(
        category="knowledge",
        name="Delete knowledge document",
        method="DELETE",
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
        request_path=(
            f"/api/knowledge/knowledge-bases/{context.knowledge_base_id}/documents/{context.document_id}"
        ),
        expected_statuses=[204],
    )
    runner.check(
        category="knowledge",
        name="Deleted knowledge document returns 404",
        method="GET",
        route_template="/api/knowledge/knowledge-bases/{knowledge_base_id}/documents/{document_id}",
        request_path=(
            f"/api/knowledge/knowledge-bases/{context.knowledge_base_id}/documents/{context.document_id}"
        ),
        expected_statuses=[404],
    )


def run_logout_checks(runner: AuditRunner) -> None:
    runner.check(
        category="auth",
        name="Logout current session",
        method="POST",
        route_template="/api/auth/logout",
        request_path="/api/auth/logout",
        expected_statuses=[200],
    )
    runner.check(
        category="auth",
        name="Refresh after logout fails",
        method="POST",
        route_template="/api/auth/refresh",
        request_path="/api/auth/refresh",
        expected_statuses=[401],
        request_kwargs={"json": {}},
    )
