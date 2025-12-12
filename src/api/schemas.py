from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    message: str
    status: Optional[str] = None
    timestamp: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: str

class CharactersListResponse(BaseModel):
    characters: List[str]

class SimulationRequest(BaseModel):
    character_names: List[str] = Field(..., min_length=2, max_length=6)
    turns: Optional[int] = Field(None, ge=1, le=10)
    setting: Optional[str] = None
    scenario: Optional[str] = None

class SimulationResponse(BaseModel):
    story: str
    participants: List[str]
    turns_executed: int
    duration_seconds: float

class CharacterDetailResponse(BaseModel):
    """Response model for detailed character information."""
    character_id: str
    character_name: str
    name: str
    background_summary: str
    personality_traits: str
    current_status: str
    narrative_context: str
    skills: Dict[str, float] = Field(default_factory=dict)
    relationships: Dict[str, float] = Field(default_factory=dict)
    current_location: str = ""
    inventory: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    structured_data: Dict[str, Any] = Field(default_factory=dict)

class FileCount(BaseModel):
    """Response model for file count information."""
    count: int
    file_type: str

class CampaignsListResponse(BaseModel):
    """Response model for campaigns list."""
    campaigns: List[str]

class CampaignCreationRequest(BaseModel):
    """Request model for campaign creation."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    participants: List[str] = Field(..., min_length=1)

class CampaignCreationResponse(BaseModel):
    """Response model for campaign creation."""
    campaign_id: str
    name: str
    status: str
    created_at: str

# Authentication Models
class LoginRequest(BaseModel):
    """Request model for user login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    remember_me: bool = Field(default=False, description="Whether to extend session duration")

class AuthResponse(BaseModel):
    """Response model for authentication endpoints."""
    access_token: str = Field(..., description="JWT access token (for backward compatibility)")
    refresh_token: str = Field(..., description="JWT refresh token (for backward compatibility)")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiry time in seconds")
    user: Dict[str, Any] = Field(..., description="User information")

class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., description="Refresh token")

class CSRFTokenResponse(BaseModel):
    """Response model for CSRF token endpoint."""
    csrf_token: str = Field(..., description="CSRF token for state-changing requests")

class InvalidationRequest(BaseModel):
    all_of: List[str]

class ChunkInRequest(BaseModel):
    seq: int
    data: str
