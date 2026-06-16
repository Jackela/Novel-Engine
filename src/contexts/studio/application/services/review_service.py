from __future__ import annotations

from src.contexts.studio.application.service_common import (
    Any,
    Principal,
    StudioRepository,
    _owner_scopes,
    _review_payload,
    utcnow,
)

__all__ = ["ReviewService"]


class ReviewService:
    """Editorial review runs."""

    def __init__(self, repository: StudioRepository) -> None:
        self._repository = repository

    def review_project(
        self,
        principal: Principal,
        project_id: str,
        *,
        provider: str = "deterministic",
        model: str = "studio-review-v1",
    ) -> dict[str, Any]:
        owner_id, guest_session_id = _owner_scopes(principal)
        review = self._repository.create_review(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
            provider=provider,
            model=model,
            now=utcnow(),
        )
        return _review_payload(review)

    def list_reviews(
        self,
        principal: Principal,
        project_id: str,
    ) -> list[dict[str, Any]]:
        owner_id, guest_session_id = _owner_scopes(principal)
        reviews = self._repository.list_reviews(
            project_id,
            owner_id=owner_id,
            guest_session_id=guest_session_id,
        )
        return [_review_payload(review) for review in reviews]
