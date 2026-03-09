"""Event-to-tag bridge for cache invalidation.

Maps domain events to cache tags and triggers invalidation of
cache entries matching those tags.
"""

from __future__ import annotations

from typing import Dict

from .registry import invalidate_by_tags

_EVENT_TAG_MAP = {
    "TemplateUpdated": lambda event: [
        f"tmpl:{event.get('template_id', '')}",
        f"tmplv:{event.get('template_version', '')}",
    ],
    "IndexRebuilt": lambda event: [f"idxv:{event.get('version', '')}"],
    "ModelConfigChanged": lambda event: [f"model:{event.get('model_name', '')}"],
    "CharacterUpdated": lambda event: [f"character:{event.get('character_id', '')}"],
}


def invalidate_event(event: Dict[str, str]) -> int:
    """Invalidate cache entries based on a domain event.

    Maps event types to cache tags and invalidates matching entries
    across all registered caches.

    Args:
        event: Domain event dictionary with 'type' and relevant fields

    Returns:
        Number of cache entries invalidated

    Example:
        >>> event = {"type": "TemplateUpdated", "template_id": "welcome"}
        >>> invalidate_event(event)
        5  # 5 entries invalidated
    """
    if not event:
        return 0
    event_type = event.get("type")
    if not event_type:
        return 0
    builder = _EVENT_TAG_MAP.get(event_type)
    if not builder:
        return 0
    tags = [t for t in builder(event) if t]
    if not tags:
        return 0
    return invalidate_by_tags(tags)
