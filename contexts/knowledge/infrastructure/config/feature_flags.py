"""
Knowledge Feature Flags

Feature flags for gradual rollout and backward compatibility during migration.

Constitution Compliance:
- Article IV (SSOT): Feature flag controls migration from Markdown to PostgreSQL
- Article VII (Observability): Feature flag state logged for operational visibility
"""

import os
from typing import Literal


class KnowledgeFeatureFlags:
    """
    Feature flags for knowledge system rollout and migration.
    
    Supports gradual migration from Markdown files to PostgreSQL-backed
    knowledge base with backward compatibility and safe rollback capability.
    
    Constitution Compliance:
        - Article IV (SSOT): Controls transition to PostgreSQL as SSOT
        - FR-018: Enables rollback capability during migration
    """
    
    # Environment variable name
    USE_KNOWLEDGE_BASE_ENV = "NOVEL_ENGINE_USE_KNOWLEDGE_BASE"
    
    @classmethod
    def use_knowledge_base(cls) -> bool:
        """
        Check if knowledge base should be used instead of Markdown files.
        
        Controls whether SubjectiveBriefPhase uses the PostgreSQL-backed
        knowledge retrieval system or falls back to legacy Markdown file reads.
        
        Environment Variable:
            NOVEL_ENGINE_USE_KNOWLEDGE_BASE: Set to enable knowledge base
            
        Values:
            - "true", "1", "yes", "on" (case-insensitive): Enable knowledge base
            - "false", "0", "no", "off" (case-insensitive): Use Markdown files
            - Not set or empty: Default to False (Markdown files)
        
        Returns:
            True if knowledge base should be used, False for Markdown fallback
        
        Examples:
            # Enable knowledge base
            os.environ["NOVEL_ENGINE_USE_KNOWLEDGE_BASE"] = "true"
            assert KnowledgeFeatureFlags.use_knowledge_base() == True
            
            # Disable knowledge base (use Markdown)
            os.environ["NOVEL_ENGINE_USE_KNOWLEDGE_BASE"] = "false"
            assert KnowledgeFeatureFlags.use_knowledge_base() == False
            
            # Default behavior (Markdown)
            del os.environ["NOVEL_ENGINE_USE_KNOWLEDGE_BASE"]
            assert KnowledgeFeatureFlags.use_knowledge_base() == False
        
        Constitution Compliance:
            - FR-017: Supports backup/migration workflow
            - FR-018: Enables rollback to Markdown-based operation
        """
        value = os.environ.get(cls.USE_KNOWLEDGE_BASE_ENV, "").lower().strip()
        
        # Truthy values
        if value in ("true", "1", "yes", "on"):
            return True
        
        # Falsy values or not set
        return False
    
    @classmethod
    def get_knowledge_source(cls) -> Literal["knowledge_base", "markdown"]:
        """
        Get current knowledge source for logging and observability.
        
        Returns:
            "knowledge_base" if using PostgreSQL, "markdown" if using files
        
        Constitution Compliance:
            - Article VII (Observability): Provides visibility into feature flag state
        """
        return "knowledge_base" if cls.use_knowledge_base() else "markdown"
    
    @classmethod
    def set_use_knowledge_base(cls, enabled: bool) -> None:
        """
        Programmatically set knowledge base feature flag.
        
        Useful for testing and controlled rollout scenarios.
        
        Args:
            enabled: True to enable knowledge base, False for Markdown
        
        Warning:
            This modifies environment variables. Use with caution in production.
            Prefer environment configuration over programmatic changes.
        """
        os.environ[cls.USE_KNOWLEDGE_BASE_ENV] = "true" if enabled else "false"
    
    @classmethod
    def clear_flag(cls) -> None:
        """
        Clear the knowledge base feature flag.
        
        Resets to default behavior (Markdown files).
        Useful for testing cleanup.
        """
        os.environ.pop(cls.USE_KNOWLEDGE_BASE_ENV, None)
