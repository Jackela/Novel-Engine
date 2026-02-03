"""Social Network Analysis API router.

This module provides endpoints for analyzing the social network formed
by character relationships. Helps writers understand social dynamics,
identify key characters, and visualize network structure.

Endpoints:
    GET /api/social/analysis - Get complete social network analysis
    GET /api/social/analysis/{character_id} - Get centrality for one character
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status

from src.api.schemas import (
    CharacterCentralitySchema,
    SocialAnalysisResponse,
)
from src.contexts.world.application.services.social_graph_service import (
    CharacterCentrality,
    SocialAnalysisResult,
    SocialGraphService,
)
from src.contexts.world.infrastructure.persistence.in_memory_relationship_repository import (
    InMemoryRelationshipRepository,
)

router = APIRouter(prefix="/social", tags=["social"])

# Reuse the same repository instance as relationships router
# In production, this would be injected via DI
_repository: Optional[InMemoryRelationshipRepository] = None
_service: Optional[SocialGraphService] = None


def get_repository() -> InMemoryRelationshipRepository:
    """Get or create the repository singleton.

    Why share with relationships router: Social analysis operates on the
    same relationship data. Sharing the repository ensures consistency
    and avoids data duplication.
    """
    global _repository
    if _repository is None:
        # Import here to get the shared instance from relationships router
        from src.api.routers.relationships import get_repository as get_rel_repo

        _repository = get_rel_repo()
    return _repository


def get_service() -> SocialGraphService:
    """Get or create the social graph service singleton."""
    global _service
    if _service is None:
        _service = SocialGraphService(get_repository())
    return _service


def _centrality_to_schema(centrality: CharacterCentrality) -> CharacterCentralitySchema:
    """Convert domain CharacterCentrality to API schema."""
    return CharacterCentralitySchema(
        character_id=centrality.character_id,
        relationship_count=centrality.relationship_count,
        positive_count=centrality.positive_count,
        negative_count=centrality.negative_count,
        average_trust=centrality.average_trust,
        average_romance=centrality.average_romance,
        centrality_score=centrality.centrality_score,
    )


def _analysis_to_response(result: SocialAnalysisResult) -> SocialAnalysisResponse:
    """Convert domain SocialAnalysisResult to API response."""
    return SocialAnalysisResponse(
        character_centralities={
            cid: _centrality_to_schema(metrics)
            for cid, metrics in result.character_centralities.items()
        },
        most_connected=result.most_connected,
        most_hated=result.most_hated,
        most_loved=result.most_loved,
        total_relationships=result.total_relationships,
        total_characters=result.total_characters,
        network_density=result.network_density,
    )


@router.get("/analysis", response_model=SocialAnalysisResponse)
async def get_social_analysis() -> SocialAnalysisResponse:
    """Get complete social network analysis.

    Analyzes all character-to-character relationships to compute centrality
    metrics, identify key characters (most connected, most hated, most loved),
    and measure network properties like density.

    Returns:
        SocialAnalysisResponse with complete network metrics.

    Example response:
        {
            "character_centralities": {
                "char-001": {
                    "character_id": "char-001",
                    "relationship_count": 5,
                    "positive_count": 3,
                    "negative_count": 1,
                    "average_trust": 65.0,
                    "average_romance": 20.0,
                    "centrality_score": 100.0
                }
            },
            "most_connected": "char-001",
            "most_hated": "char-003",
            "most_loved": "char-002",
            "total_relationships": 10,
            "total_characters": 4,
            "network_density": 0.83
        }
    """
    service = get_service()
    result = await service.analyze_social_network()
    return _analysis_to_response(result)


@router.get("/analysis/{character_id}", response_model=CharacterCentralitySchema)
async def get_character_centrality(character_id: str) -> CharacterCentralitySchema:
    """Get centrality metrics for a specific character.

    Computes how central this character is in the social network based on
    their relationships with other characters.

    Args:
        character_id: ID of the character to analyze.

    Returns:
        CharacterCentralitySchema with the character's metrics.

    Raises:
        HTTPException 404: If character has no relationships.
    """
    service = get_service()
    centrality = await service.get_character_centrality(character_id)

    if centrality is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No relationships found for character: {character_id}",
        )

    return _centrality_to_schema(centrality)
