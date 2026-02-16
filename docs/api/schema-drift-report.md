# Schema Synchronization Audit Report
**Generated:** 2026-02-03**Backend Schemas:** 143**Frontend Schemas:** 103## Summary
### Missing in Frontend (53)
The following backend schemas have no corresponding frontend schema:
- `AnalyticsMetricsData`
- `CSRFTokenResponse`
- `CampaignCreationRequest`
- `CampaignDetailResponse`
- `CampaignsListResponse`
- `ChapterUpdateRequest`
- `CharacterCentralitySchema`
- `CharacterGoalSchema`
- `CharacterMemoriesResponse`
- `CharacterMemoryCreateRequest`
- `CharacterMemorySchema`
- `CharacterMemoryUpdateRequest`
- `CharacterPsychologySchema`
- `ChunkInRequest`
- `FactionJoinRequest`
- `FactionLeaveRequest`
- `FactionMemberSchema`
- `FactionSetLeaderResponse`
- `FileCount`
- `HealthResponse`
- `HealthCheckResponse`
- `InteractionLogSchema`
- `InvalidationRequest`
- `ItemCreateRequest`
- `ItemUpdateRequest`
- `LogInteractionRequest`
- `LogoutResponse`
- `LoreEntryCreateRequest`
- `LoreEntryUpdateRequest`
- `LoreSearchRequest`
- `MoveChapterRequest`
- `MoveSceneRequest`
- `NarrativeData`
- `NarrativeStreamRequest`
- `NarrativeStreamChunk`
- `NarrativeStreamMetadata`
- `OrchestrationStopResponse`
- `PolicyInfoResponse`
- `RefreshTokenRequest`
- `RelationshipCreateRequest`
- `RelationshipUpdateRequest`
- `SSEEventData`
- `SSEStatsResponse`
- `SceneUpdateRequest`
- `SimulationRequest`
- `StoryUpdateRequest`
- `StructureErrorResponse`
- `SystemStatusResponse`
- `TokenValidationResponse`
- `WorkspaceCharacterCreateRequest`
- `WorkspaceCharacterUpdateRequest`
- `WorldContext`
- `WorldContextEntity`

### Missing in Backend (18)
The following frontend schemas have no corresponding backend schema:
- `AuthToken`
- `AuthUser`
- `Campaign`
- `CharacterCentrality`
- `CharacterGoal`
- `CharacterMemory`
- `CharacterPsychology`
- `ErrorInfo`
- `Faction`
- `FactionMember`
- `HistoryEvent`
- `InlineCharacterGoal`
- `InteractionLog`
- `LocationListResponse`
- `WorkspaceCharacterUpdate`
- `WorldGenerationRequest`
- `WorldLocation`
- `WorldSetting`


## Field-Level Mismatches

### CRITICAL Issues (67)
#### `AuthResponse`
- **Issue:** Type mismatch in field 'expires_in'
  - Type mismatch: backend=int, frontend=int | float

#### `BeatResponse`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=int, frontend=int | float

#### `BeatResponse`
- **Issue:** Type mismatch in field 'mood_shift'
  - Type mismatch: backend=int, frontend=int | float

#### `BeatCreateRequest`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=Optional[int], frontend=int | float

#### `BeatCreateRequest`
- **Issue:** Type mismatch in field 'mood_shift'
  - Type mismatch: backend=int, frontend=int | float

#### `BeatUpdateRequest`
- **Issue:** Type mismatch in field 'mood_shift'
  - Type mismatch: backend=Optional[int], frontend=int | float

#### `ChapterResponse`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=int, frontend=int | float

#### `ChapterResponse`
- **Issue:** Type mismatch in field 'status'
  - Type mismatch: backend=str, frontend=Enum

#### `ChapterResponse`
- **Issue:** Type mismatch in field 'scene_count'
  - Type mismatch: backend=int, frontend=int | float

#### `ChapterCreateRequest`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=Optional[int], frontend=int | float

#### `ChapterHealthReportResponse`
- **Issue:** Type mismatch in field 'total_beats'
  - Type mismatch: backend=int, frontend=int | float

#### `ChapterHealthReportResponse`
- **Issue:** Type mismatch in field 'total_scenes'
  - Type mismatch: backend=int, frontend=int | float

#### `ChapterPacingResponse`
- **Issue:** Type mismatch in field 'average_tension'
  - Type mismatch: backend=float, frontend=int | float

#### `ChapterPacingResponse`
- **Issue:** Type mismatch in field 'average_energy'
  - Type mismatch: backend=float, frontend=int | float

#### `ChapterPacingResponse`
- **Issue:** Type mismatch in field 'tension_range'
  - Type mismatch: backend=List[int], frontend=tuple

#### `ChapterPacingResponse`
- **Issue:** Type mismatch in field 'energy_range'
  - Type mismatch: backend=List[int], frontend=tuple

#### `CharacterGoalsResponse`
- **Issue:** Type mismatch in field 'completed_count'
  - Type mismatch: backend=int, frontend=int | float

#### `CharacterGoalsResponse`
- **Issue:** Type mismatch in field 'active_count'
  - Type mismatch: backend=int, frontend=int | float

#### `CharacterGoalsResponse`
- **Issue:** Type mismatch in field 'total_count'
  - Type mismatch: backend=int, frontend=int | float

#### `CharacterGoalsResponse`
- **Issue:** Type mismatch in field 'failed_count'
  - Type mismatch: backend=int, frontend=int | float

#### `CritiqueCategoryScoreResponse`
- **Issue:** Type mismatch in field 'score'
  - Type mismatch: backend=int, frontend=int | float

#### `FactionDetailResponse`
- **Issue:** Type mismatch in field 'influence'
  - Type mismatch: backend=int, frontend=int | float

#### `FactionDetailResponse`
- **Issue:** Type mismatch in field 'member_count'
  - Type mismatch: backend=int, frontend=int | float

#### `HealthWarningResponse`
- **Issue:** Type mismatch in field 'severity'
  - Type mismatch: backend=str, frontend=Enum

#### `ItemResponse`
- **Issue:** Type mismatch in field 'weight'
  - Type mismatch: backend=Optional[float], frontend=int | float

#### `ItemResponse`
- **Issue:** Type mismatch in field 'value'
  - Type mismatch: backend=Optional[int], frontend=int | float

#### `ItemListResponse`
- **Issue:** Type mismatch in field 'total'
  - Type mismatch: backend=int, frontend=int | float

#### `LoreEntryListResponse`
- **Issue:** Type mismatch in field 'total'
  - Type mismatch: backend=int, frontend=int | float

#### `OrchestrationStartRequest`
- **Issue:** Type mismatch in field 'total_turns'
  - Type mismatch: backend=Optional[int], frontend=int | float

#### `OrchestrationStatusData`
- **Issue:** Type mismatch in field 'current_turn'
  - Type mismatch: backend=int, frontend=int | float

#### `OrchestrationStatusData`
- **Issue:** Type mismatch in field 'average_processing_time'
  - Type mismatch: backend=float, frontend=int | float

#### `OrchestrationStatusData`
- **Issue:** Type mismatch in field 'total_turns'
  - Type mismatch: backend=int, frontend=int | float

#### `OrchestrationStatusData`
- **Issue:** Type mismatch in field 'queue_length'
  - Type mismatch: backend=int, frontend=int | float

#### `OrchestrationStep`
- **Issue:** Type mismatch in field 'progress'
  - Type mismatch: backend=float, frontend=int | float

#### `PacingIssueResponse`
- **Issue:** Type mismatch in field 'severity'
  - Type mismatch: backend=str, frontend=Enum

#### `PhaseDistributionResponse`
- **Issue:** Type mismatch in field 'rising_action'
  - Type mismatch: backend=int, frontend=int | float

#### `PhaseDistributionResponse`
- **Issue:** Type mismatch in field 'climax'
  - Type mismatch: backend=int, frontend=int | float

#### `PhaseDistributionResponse`
- **Issue:** Type mismatch in field 'resolution'
  - Type mismatch: backend=int, frontend=int | float

#### `PhaseDistributionResponse`
- **Issue:** Type mismatch in field 'setup'
  - Type mismatch: backend=int, frontend=int | float

#### `PhaseDistributionResponse`
- **Issue:** Type mismatch in field 'inciting_incident'
  - Type mismatch: backend=int, frontend=int | float

#### `RelationshipResponse`
- **Issue:** Type mismatch in field 'strength'
  - Type mismatch: backend=int, frontend=int | float

#### `RelationshipResponse`
- **Issue:** Type mismatch in field 'trust'
  - Type mismatch: backend=int, frontend=int | float

#### `RelationshipResponse`
- **Issue:** Type mismatch in field 'romance'
  - Type mismatch: backend=int, frontend=int | float

#### `RelationshipListResponse`
- **Issue:** Type mismatch in field 'total'
  - Type mismatch: backend=int, frontend=int | float

#### `SceneResponse`
- **Issue:** Type mismatch in field 'beat_count'
  - Type mismatch: backend=int, frontend=int | float

#### `SceneResponse`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=int, frontend=int | float

#### `SceneResponse`
- **Issue:** Type mismatch in field 'status'
  - Type mismatch: backend=str, frontend=Enum

#### `SceneCreateRequest`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=Optional[int], frontend=int | float

#### `ScenePacingMetricsResponse`
- **Issue:** Type mismatch in field 'energy_level'
  - Type mismatch: backend=int, frontend=int | float

#### `ScenePacingMetricsResponse`
- **Issue:** Type mismatch in field 'order_index'
  - Type mismatch: backend=int, frontend=int | float

#### `ScenePacingMetricsResponse`
- **Issue:** Type mismatch in field 'tension_level'
  - Type mismatch: backend=int, frontend=int | float

#### `SocialAnalysisResponse`
- **Issue:** Type mismatch in field 'total_characters'
  - Type mismatch: backend=int, frontend=int | float

#### `SocialAnalysisResponse`
- **Issue:** Type mismatch in field 'total_relationships'
  - Type mismatch: backend=int, frontend=int | float

#### `SocialAnalysisResponse`
- **Issue:** Type mismatch in field 'network_density'
  - Type mismatch: backend=float, frontend=int | float

#### `StoryResponse`
- **Issue:** Type mismatch in field 'chapter_count'
  - Type mismatch: backend=int, frontend=int | float

#### `StoryResponse`
- **Issue:** Type mismatch in field 'status'
  - Type mismatch: backend=str, frontend=Enum

#### `TensionArcShapeResponse`
- **Issue:** Type mismatch in field 'ends_at'
  - Type mismatch: backend=int, frontend=int | float

#### `TensionArcShapeResponse`
- **Issue:** Type mismatch in field 'peaks_at'
  - Type mismatch: backend=int, frontend=int | float

#### `TensionArcShapeResponse`
- **Issue:** Type mismatch in field 'starts_at'
  - Type mismatch: backend=int, frontend=int | float

#### `WordCountEstimateResponse`
- **Issue:** Type mismatch in field 'min_words'
  - Type mismatch: backend=int, frontend=int | float

#### `WordCountEstimateResponse`
- **Issue:** Type mismatch in field 'total_words'
  - Type mismatch: backend=int, frontend=int | float

#### `WordCountEstimateResponse`
- **Issue:** Type mismatch in field 'max_words'
  - Type mismatch: backend=int, frontend=int | float

#### `WordCountEstimateResponse`
- **Issue:** Type mismatch in field 'per_scene_average'
  - Type mismatch: backend=float, frontend=int | float

#### `WorldRuleResponse`
- **Issue:** Type mismatch in field 'severity'
  - Type mismatch: backend=int, frontend=int | float

#### `WorldRuleCreateRequest`
- **Issue:** Type mismatch in field 'severity'
  - Type mismatch: backend=int, frontend=int | float

#### `WorldRuleListResponse`
- **Issue:** Type mismatch in field 'total'
  - Type mismatch: backend=int, frontend=int | float

#### `WorldRuleUpdateRequest`
- **Issue:** Type mismatch in field 'severity'
  - Type mismatch: backend=Optional[int], frontend=int | float


### HIGH Issues (22)
#### `AuthResponse`
- **Issue:** Fields missing in frontend
  - user

#### `BeatResponse`
- **Issue:** Fields missing in frontend
  - beat_type

#### `BeatCreateRequest`
- **Issue:** Fields missing in frontend
  - beat_type

#### `BeatSuggestionRequest`
- **Issue:** Fields missing in frontend
  - scene_context
  - mood_target
  - current_beats

#### `BeatUpdateRequest`
- **Issue:** Fields missing in frontend
  - beat_type

#### `ChapterHealthReportResponse`
- **Issue:** Fields missing in frontend
  - health_score
  - phase_distribution
  - word_count
  - tension_arc

#### `CharacterDetailResponse`
- **Issue:** Fields missing in frontend
  - psychology

#### `CharacterGoalCreateRequest`
- **Issue:** Fields missing in frontend
  - urgency

#### `ConflictResponse`
- **Issue:** Fields missing in frontend
  - conflict_type
  - stakes
  - resolution_status

#### `ConflictCreateRequest`
- **Issue:** Fields missing in frontend
  - conflict_type
  - stakes
  - resolution_status

#### `ConflictUpdateRequest`
- **Issue:** Fields missing in frontend
  - conflict_type
  - stakes
  - resolution_status

#### `ForeshadowingResponse`
- **Issue:** Fields missing in frontend
  - status

#### `ForeshadowingCreateRequest`
- **Issue:** Fields missing in frontend
  - status

#### `ForeshadowingUpdateRequest`
- **Issue:** Fields missing in frontend
  - status

#### `ItemResponse`
- **Issue:** Fields missing in frontend
  - item_type
  - rarity

#### `LoreEntryResponse`
- **Issue:** Fields missing in frontend
  - updated_at
  - id
  - summary
  - related_entry_ids
  - created_at
  - category

#### `PlotlineResponse`
- **Issue:** Fields missing in frontend
  - status

#### `PlotlineCreateRequest`
- **Issue:** Fields missing in frontend
  - status

#### `PlotlineUpdateRequest`
- **Issue:** Fields missing in frontend
  - status

#### `RelationshipResponse`
- **Issue:** Fields missing in frontend
  - relationship_type
  - target_type
  - source_type

#### `SceneResponse`
- **Issue:** Fields missing in frontend
  - story_phase

#### `SceneCreateRequest`
- **Issue:** Fields missing in frontend
  - story_phase


### MEDIUM Issues (3)
#### `AuthResponse`
- **Issue:** Fields missing in backend
  - refresh_expires_in

#### `BeatSuggestionRequest`
- **Issue:** Fields missing in backend
  - content
  - beat_type
  - mood_shift

#### `CharacterSummary`
- **Issue:** Fields missing in backend
  - faction_id


## Recommendations

### Priority Actions
1. **Regenerate Frontend Schemas**: Run `python scripts/generate_openapi.py` and use the output to update `frontend/src/types/schemas.ts`
2. **Add Missing Frontend Schemas**: Create Zod schemas for all backend schemas marked as "Missing in Frontend"
3. **Fix Critical Type Mismatches**: Align field types between Pydantic and Zod schemas
4. **Remove Unused Frontend Schemas**: Review schemas marked as "Missing in Backend" and remove if not needed

### Process
1. Update backend schema in `src/api/schemas.py`
2. Run `python scripts/generate_openapi.py` to regenerate OpenAPI spec
3. Use the OpenAPI spec to update `frontend/src/types/schemas.ts` (or use automation tools)
4. Run `npm run type-check` to verify alignment

### Verification
Run these commands to verify schema synchronization:
```bash
# Backend
python scripts/generate_openapi.py

# Frontend
npm run type-check
npm run lint:all
```
