"""Honcho infrastructure configuration.

This module provides Pydantic-based configuration for Honcho memory system,
following the existing settings pattern in the project.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class HonchoSettings(BaseSettings):
    """Honcho memory system configuration.

    Supports both cloud (app.honcho.dev) and self-hosted deployments.
    """

    model_config = SettingsConfigDict(
        env_prefix="HONCHO_",
        extra="ignore",
        case_sensitive=False,
    )

    # Connection settings
    api_key: str | None = Field(
        default=None,
        description="Honcho API key (required for cloud deployment)",
    )
    base_url: str = Field(
        default="http://localhost:8000",
        description="Honcho API base URL",
    )

    # Deployment mode
    deployment: Literal["cloud", "self_hosted"] = Field(
        default="self_hosted",
        description="Honcho deployment mode",
    )

    # Default workspace configuration
    default_workspace_name: str = Field(
        default="novel-engine",
        description="Default workspace name for the application",
    )

    # Workspace strategy: how to organize workspaces
    # "story": Each story gets its own workspace (recommended)
    # "character": Each character gets its own workspace
    workspace_strategy: Literal["story", "character"] = Field(
        default="story",
        description="How to organize Honcho workspaces",
    )

    # Request settings
    timeout: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts",
    )
    retry_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Delay between retries in seconds",
    )

    # Memory settings
    default_session_ttl_days: int = Field(
        default=365,
        ge=1,
        le=3650,
        description="Default session TTL in days",
    )
    max_memories_per_query: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum memories to retrieve per query",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base_url ends without trailing slash."""
        return v.rstrip("/")

    @field_validator("deployment", mode="before")
    @classmethod
    def validate_deployment(cls, v: str) -> str:
        """Normalize deployment value."""
        v = v.lower().strip()
        if v in ("cloud", "managed"):
            return "cloud"
        elif v in ("self_hosted", "self-hosted", "local"):
            return "self_hosted"
        raise ValueError(f"Invalid deployment mode: {v}")

    @property
    def is_cloud(self) -> bool:
        """Check if using cloud deployment."""
        return self.deployment == "cloud"

    @property
    def is_self_hosted(self) -> bool:
        """Check if using self-hosted deployment."""
        return self.deployment == "self_hosted"

    def get_workspace_id(self, story_id: str | None = None) -> str:
        """Generate workspace ID for a story.

        Args:
            story_id: Optional story identifier. If None, uses default workspace.

        Returns:
            Workspace identifier string.
        """
        if story_id:
            return f"{self.default_workspace_name}-{story_id}"
        return self.default_workspace_name

    def get_workspace_for_story(self, story_id: str) -> str:
        """Get workspace ID for a story using story-centric strategy.

        Args:
            story_id: The story identifier.

        Returns:
            Workspace identifier in format: {default_workspace_name}-{story_id}
        """
        return f"{self.default_workspace_name}-{story_id}"

    def get_workspace_for_character(
        self,
        character_id: str,
        story_id: str | None = None,
    ) -> str:
        """Get workspace ID for a character.

        Uses story-centric strategy: if story_id is provided, all characters
        in a story share the same workspace.

        Args:
            character_id: The character identifier.
            story_id: Optional story identifier for story-centric mode.

        Returns:
            Workspace identifier.
        """
        if self.workspace_strategy == "story" and story_id:
            return self.get_workspace_for_story(story_id)
        return f"{self.default_workspace_name}-{character_id}"
