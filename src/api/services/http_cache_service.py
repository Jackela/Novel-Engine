#!/usr/bin/env python3
"""
HTTP Cache Service

Why this module exists:
    The characters router contained logic for HTTP caching (ETag, Last-Modified).
    This service extracts that logic to make it reusable across routers.

Key patterns:
    - ETags are SHA256 hashes of entity identifiers and timestamps
    - Collection ETags are hashes of all item IDs and timestamps
    - Cache-Control headers are set via Response objects

Gotchas:
    - ETag headers must be quoted (RFC 7232)
    - If-None-Match may contain multiple ETags separated by commas
    - If-Modified-Since uses HTTP-date format, not ISO
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from email.utils import format_datetime
from typing import Any, Dict, List, Optional

from fastapi import Request, Response

from src.api.schemas import CharacterSummary

logger = logging.getLogger(__name__)


class HttpCacheService:
    """
    Service for HTTP caching logic (ETag, Last-Modified headers).

    This service provides methods for building cache headers, checking
    conditional requests, and setting cache headers on responses.
    """

    def __init__(self) -> None:
        """Initialize the cache service."""
        self.logger = logger.getChild(self.__class__.__name__)

    def build_etag(self, identifier: str, updated: datetime) -> str:
        """
        Build an ETag for a single entity.

        Why: ETags enable conditional requests (304 Not Modified) for efficient caching.

        Args:
            identifier: Entity identifier (e.g., character_id)
            updated: Last modified datetime

        Returns:
            Hexadecimal SHA256 hash
        """
        payload = f"{identifier}:{updated.isoformat()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def build_collection_etag(
        self, summaries: List[CharacterSummary]
    ) -> str:
        """
        Build an ETag for a collection of entities.

        Why: Collection ETags should only include identity and timestamps,
        not the full entity data.

        Args:
            summaries: List of entity summaries

        Returns:
            Hexadecimal SHA256 hash
        """
        payload = [
            {
                "id": summary.id,
                "updated_at": summary.updated_at,
                "workspace_id": summary.workspace_id,
            }
            for summary in summaries
        ]
        serialized = json.dumps(
            payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def set_cache_headers(
        self, response: Response, etag: str, latest: Optional[datetime]
    ) -> None:
        """
        Set cache headers on a response.

        Args:
            response: FastAPI Response object
            etag: ETag value (will be quoted)
            latest: Optional last-modified datetime
        """
        response.headers["ETag"] = f'"{etag}"'
        if latest:
            try:
                response.headers["Last-Modified"] = format_datetime(latest, usegmt=True)
            except Exception:
                response.headers["Last-Modified"] = format_datetime(latest)

    def etag_matches(self, request_etag: str, current_etag: str) -> bool:
        """
        Check if a request's ETag matches the current ETag.

        Why: If-None-Match may contain multiple ETags; check if current is among them.

        Args:
            request_etag: Value from If-None-Match header
            current_etag: Current entity ETag

        Returns:
            True if current_etag is in the request's list
        """
        tokens = [token.strip().strip('"') for token in request_etag.split(",")]
        return current_etag in tokens

    def is_not_modified(
        self, request: Request, etag: str, latest: Optional[datetime]
    ) -> bool:
        """
        Check if a conditional request indicates content is not modified.

        Why: Checks both If-None-Match (ETag) and If-Modified-Since (date).

        Args:
            request: FastAPI Request object
            etag: Current entity ETag
            latest: Optional last-modified datetime

        Returns:
            True if the client's cached version is current
        """
        client_etag = request.headers.get("if-none-match")
        if client_etag and self.etag_matches(client_etag, etag):
            return True

        client_since = request.headers.get("if-modified-since")
        if client_since and latest:
            since_dt = self._parse_iso_datetime(client_since)
            if since_dt and since_dt >= latest:
                return True

        return False

    def _parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """
        Parse an ISO datetime string or HTTP-date.

        Args:
            value: Datetime string

        Returns:
            Parsed datetime or None
        """
        if not value:
            return None
        try:
            from datetime import timezone

            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            try:
                from email.utils import parsedate_to_datetime

                return parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None
