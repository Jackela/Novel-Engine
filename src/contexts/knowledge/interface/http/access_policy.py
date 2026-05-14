"""HTTP access policy helpers for knowledge bases."""

from __future__ import annotations

from fastapi import HTTPException, status

from src.apps.api.dependencies import CurrentUser
from src.contexts.knowledge.application.services.knowledge_service import (
    KnowledgeApplicationService,
)
from src.contexts.knowledge.domain.aggregates.knowledge_base import KnowledgeBase
from src.contexts.knowledge.interface.http.error_handlers import ResultErrorHandler


async def authorize_knowledge_base(
    *,
    service: KnowledgeApplicationService,
    knowledge_base_id: str,
    current_user: CurrentUser | None,
    write: bool,
) -> KnowledgeBase:
    """Authorize access to a knowledge base and return the aggregate."""
    if write and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    kb = ResultErrorHandler.handle(
        await service.get_knowledge_base(knowledge_base_id)
    )
    is_owner = current_user is not None and kb.owner_id == current_user.user_id
    if write:
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found",
            )
        return kb

    if is_owner or kb.is_public:
        return kb

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Knowledge base not found",
    )


__all__ = ["authorize_knowledge_base"]
