"""Lore API schemas for the Novel Engine.

This module contains schemas for lore and world-building including:
- Lore Entry schemas (WORLD-010)
- Smart Tag Management schemas
- World Rule schemas

Created as part of PREP-002 (Operation Vanguard).
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# === Lore Entry Schemas (WORLD-010) ===


class LoreEntryCreateRequest(BaseModel):
    """Request model for creating a lore entry."""

    title: str = Field(..., min_length=1, max_length=300, description="Entry title")
    content: str = Field(default="", description="Full content (markdown supported)")
    tags: List[str] = Field(
        default_factory=list, max_length=20, description="Searchable tags"
    )
    category: str = Field(
        default="history", description="Category: HISTORY, CULTURE, MAGIC, TECHNOLOGY"
    )
    summary: str = Field(default="", max_length=500, description="Short summary")


class LoreEntryUpdateRequest(BaseModel):
    """Request model for updating a lore entry."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    content: Optional[str] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None)
    summary: Optional[str] = Field(default=None, max_length=500)


class LoreEntryResponse(BaseModel):
    """Response model for a single lore entry."""

    id: str = Field(..., description="Entry UUID")
    title: str
    content: str
    tags: List[str] = Field(default_factory=list)
    category: str
    summary: str
    related_entry_ids: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Flexible metadata including smart tags"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


# === Smart Tag Management Schemas ===


class SmartTagsResponse(BaseModel):
    """Response model for smart tags."""

    smart_tags: Dict[str, List[str]] = Field(
        default_factory=dict, description="Auto-generated smart tags by category"
    )
    manual_smart_tags: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Manual-only smart tags by category (never overridden)",
    )
    effective_tags: Dict[str, List[str]] = Field(
        default_factory=dict, description="Combined tags (auto + manual) by category"
    )


class ManualSmartTagsUpdateRequest(BaseModel):
    """Request model for updating manual smart tags."""

    category: str = Field(
        ..., description="Tag category (e.g., 'genre', 'mood', 'themes')"
    )
    tags: List[str] = Field(..., description="List of manual tags for this category")
    replace: bool = Field(
        default=False,
        description="If True, replace existing tags. If False, append to existing.",
    )


class LoreEntryListResponse(BaseModel):
    """Response model for listing lore entries."""

    entries: List[LoreEntryResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching entries")


class LoreSearchRequest(BaseModel):
    """Request model for searching lore entries."""

    query: str = Field(default="", description="Search query (matches title)")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    category: Optional[str] = Field(default=None, description="Filter by category")


# === World Rule Schemas ===


class WorldRuleCreateRequest(BaseModel):
    """Request model for creating a world rule."""

    name: str = Field(..., min_length=1, max_length=200, description="Rule name")
    description: str = Field(
        default="", max_length=5000, description="Rule description"
    )
    consequence: str = Field(
        default="",
        max_length=2000,
        description="What happens when rule is invoked/violated",
    )
    exceptions: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Cases where rule doesn't apply",
    )
    category: str = Field(
        default="",
        max_length=50,
        description="Rule category (magic, physics, social, etc.)",
    )
    severity: int = Field(
        default=50, ge=0, le=100, description="How strictly enforced (0-100)"
    )


class WorldRuleUpdateRequest(BaseModel):
    """Request model for updating a world rule."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    consequence: Optional[str] = Field(default=None, max_length=2000)
    exceptions: Optional[List[str]] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None, max_length=50)
    severity: Optional[int] = Field(default=None, ge=0, le=100)


class WorldRuleResponse(BaseModel):
    """Response model for a single world rule."""

    id: str = Field(..., description="Rule UUID")
    name: str
    description: str
    consequence: str
    exceptions: List[str] = Field(default_factory=list)
    category: str
    severity: int
    related_rule_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    updated_at: str = Field(..., description="ISO 8601 last update timestamp")


class WorldRuleListResponse(BaseModel):
    """Response model for listing world rules."""

    rules: List[WorldRuleResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total count of matching rules")
