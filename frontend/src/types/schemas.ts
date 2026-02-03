import { z } from 'zod';

// Character Psychology Schema (Big Five / OCEAN model)
// All traits scored 0-100: 0-30 = Low, 31-70 = Average, 71-100 = High
export const CharacterPsychologySchema = z.object({
  openness: z.number().min(0).max(100),
  conscientiousness: z.number().min(0).max(100),
  extraversion: z.number().min(0).max(100),
  agreeableness: z.number().min(0).max(100),
  neuroticism: z.number().min(0).max(100),
});

// Character Memory Schema
// Importance scale (1-10):
// - 1-3: Minor memories (daily routines, passing encounters)
// - 4-6: Moderate memories (friendships, minor conflicts)
// - 7-8: Significant memories (major life events, turning points)
// - 9-10: Core memories (defining moments, traumas, transformations)
export const CharacterMemorySchema = z.object({
  memory_id: z.string(),
  content: z.string().min(1),
  importance: z.number().min(1).max(10),
  tags: z.array(z.string()),
  timestamp: z.string(),
  is_core_memory: z.boolean(),
  importance_level: z.enum(['minor', 'moderate', 'significant', 'core']),
});

export const CharacterSummarySchema = z.object({
  id: z.string(),
  agent_id: z.string(),
  name: z.string(),
  status: z.string(),
  type: z.string(),
  updated_at: z.string(),
  workspace_id: z.string().nullable().optional(),
  // New fields for WORLD-001: Enhanced character profiles
  aliases: z.array(z.string()).optional().default([]),
  archetype: z.string().nullable().optional(),
  traits: z.array(z.string()).optional().default([]),
  appearance: z.string().nullable().optional(),
  // CHAR-037: Faction membership for sidebar sorting
  faction_id: z.string().nullable().optional(),
});

export const CharactersListResponseSchema = z.object({
  characters: z.array(CharacterSummarySchema),
});

/**
 * Inline goal schema for CharacterDetail (defined before CharacterGoalSchema export).
 * This matches the structure expected by the goals list component.
 */
const InlineCharacterGoalSchema = z.object({
  goal_id: z.string(),
  description: z.string().min(1),
  status: z.enum(['ACTIVE', 'COMPLETED', 'FAILED']),
  urgency: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  created_at: z.string(),
  completed_at: z.string().nullable().optional(),
  is_active: z.boolean(),
  is_urgent: z.boolean(),
});

export const CharacterDetailSchema = z.object({
  agent_id: z.string(),
  character_id: z.string(),
  character_name: z.string(),
  name: z.string(),
  background_summary: z.string(),
  personality_traits: z.string(),
  current_status: z.string(),
  narrative_context: z.string(),
  skills: z.record(z.string(), z.number()),
  relationships: z.record(z.string(), z.number()),
  current_location: z.string(),
  inventory: z.array(z.string()),
  metadata: z.record(z.string(), z.unknown()),
  structured_data: z.record(z.string(), z.unknown()),
  psychology: CharacterPsychologySchema.nullable().optional(),
  memories: z.array(CharacterMemorySchema).optional().default([]),
  goals: z.array(InlineCharacterGoalSchema).optional().default([]),
});

export const WorkspaceCharacterCreateSchema = z.object({
  agent_id: z.string().min(1, 'Agent ID is required'),
  name: z.string().min(2, 'Name must be at least 2 characters').max(100),
  background_summary: z.string().max(1000).optional().default(''),
  personality_traits: z.string().max(500).optional().default(''),
  skills: z.record(z.string(), z.number()).optional().default({}),
  relationships: z.record(z.string(), z.number()).optional().default({}),
  current_location: z.string().max(200).optional().default(''),
  inventory: z.array(z.string()).optional().default([]),
  metadata: z.record(z.string(), z.unknown()).optional().default({}),
  structured_data: z.record(z.string(), z.unknown()).optional().default({}),
});

export const WorkspaceCharacterUpdateSchema = z.object({
  name: z.string().min(2).max(100).optional(),
  background_summary: z.string().max(1000).optional(),
  personality_traits: z.string().max(500).optional(),
  skills: z.record(z.string(), z.number()).optional(),
  relationships: z.record(z.string(), z.number()).optional(),
  current_location: z.string().max(200).optional(),
  inventory: z.array(z.string()).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
  structured_data: z.record(z.string(), z.unknown()).optional(),
});

export const AuthUserSchema = z.object({
  id: z.string(),
  username: z.string(),
  email: z.string(),
  roles: z.array(z.string()),
});

export const LoginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string(),
  remember_me: z.boolean().optional(),
});

export const AuthResponseSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string(),
  token_type: z.string(),
  expires_in: z.number(),
  refresh_expires_in: z.number().optional(),
  user: AuthUserSchema,
});

export const AuthTokenSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string(),
  tokenType: z.string(),
  expiresAt: z.number(),
  refreshExpiresAt: z.number(),
  user: AuthUserSchema,
});

export const GuestSessionResponseSchema = z.object({
  workspace_id: z.string(),
  created: z.boolean().optional(),
});

export const CampaignSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  status: z.enum(['active', 'completed', 'archived']),
  created_at: z.string(),
  updated_at: z.string(),
  current_turn: z.number(),
});

export const CampaignDetailResponseSchema = CampaignSchema;

export const OrchestrationStartRequestSchema = z.object({
  character_names: z.array(z.string().min(1)).min(2).max(6).optional(),
  total_turns: z.number().int().min(1).max(10).optional(),
  setting: z.string().min(1).optional(),
  scenario: z.string().min(1).optional(),
});

export const OrchestrationStepSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  progress: z.number(),
});

export const OrchestrationStatusSchema = z.object({
  status: z.string(),
  current_turn: z.number(),
  total_turns: z.number(),
  queue_length: z.number(),
  average_processing_time: z.number(),
  steps: z.array(OrchestrationStepSchema),
  last_updated: z.string().nullable().optional(),
});

export const OrchestrationStatusResponseSchema = z.object({
  success: z.boolean(),
  data: OrchestrationStatusSchema,
  message: z.string().optional(),
});

export const OrchestrationStartResponseSchema = z.object({
  success: z.boolean(),
  status: z.string(),
  task_id: z.string().optional(),
  message: z.string().optional(),
});

export const CharacterGenerationRequestSchema = z.object({
  concept: z.string(),
  archetype: z.string(),
  tone: z.string().optional(),
});

export const CharacterGenerationResponseSchema = z.object({
  name: z.string(),
  tagline: z.string(),
  bio: z.string(),
  visual_prompt: z.string(),
  traits: z.array(z.string()),
});

// Character Profile Generation Schemas (WORLD-013)
export const CharacterProfileGenerationRequestSchema = z.object({
  name: z.string().min(1).max(100),
  archetype: z.string().min(1).max(50),
  context: z.string().max(500).optional(),
});

export const CharacterProfileGenerationResponseSchema = z.object({
  name: z.string(),
  aliases: z.array(z.string()),
  archetype: z.string(),
  traits: z.array(z.string()),
  appearance: z.string(),
  backstory: z.string(),
  motivations: z.array(z.string()),
  quirks: z.array(z.string()),
});

export const SceneGenerationRequestSchema = z.object({
  character_context: CharacterGenerationResponseSchema,
  scene_type: z.string(),
  tone: z.string().optional(),
});

export const SceneGenerationResponseSchema = z.object({
  title: z.string(),
  content: z.string(),
  summary: z.string(),
  visual_prompt: z.string(),
});

// World Generation Schemas
export const WorldGenerationRequestSchema = z.object({
  genre: z.string().default('fantasy'),
  era: z.string().default('medieval'),
  tone: z.string().default('heroic'),
  themes: z.array(z.string()).default(['adventure', 'heroism']),
  magic_level: z.number().min(0).max(10).default(5),
  technology_level: z.number().min(0).max(10).default(3),
  num_factions: z.number().min(1).max(10).default(3),
  num_locations: z.number().min(1).max(10).default(5),
  num_events: z.number().min(1).max(10).default(3),
});

export const WorldSettingSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  genre: z.string(),
  era: z.string(),
  tone: z.string(),
  themes: z.array(z.string()),
  magic_level: z.number(),
  technology_level: z.number(),
});

export const FactionSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  faction_type: z.string(),
  alignment: z.string(),
  values: z.array(z.string()),
  goals: z.array(z.string()),
  influence: z.number(),
  ally_count: z.number(),
  enemy_count: z.number(),
});

/**
 * LocationType enum values matching backend LocationType enum.
 * Used for rendering appropriate icons in LocationTree component.
 */
export const LocationTypeEnum = z.enum([
  'continent',
  'region',
  'country',
  'province',
  'city',
  'town',
  'village',
  'fortress',
  'castle',
  'dungeon',
  'temple',
  'forest',
  'mountain',
  'ocean',
  'river',
  'desert',
  'swamp',
  'plains',
  'island',
  'cave',
  'ruins',
  'landmark',
  'capital',
  'port',
  'space_station',
  'planet',
  'dimension',
]);

export type LocationType = z.infer<typeof LocationTypeEnum>;

export const WorldLocationSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  location_type: z.string(),
  population: z.number(),
  controlling_faction_id: z.string().nullable(),
  notable_features: z.array(z.string()),
  danger_level: z.string(),
  // Hierarchy fields for tree structure
  parent_location_id: z.string().nullable().optional(),
  child_location_ids: z.array(z.string()).optional().default([]),
});

export const LocationListResponseSchema = z.object({
  locations: z.array(WorldLocationSchema),
});

export const HistoryEventSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  event_type: z.string(),
  significance: z.number(),
  participants: z.array(z.string()),
});

export const WorldGenerationResponseSchema = z.object({
  world_setting: WorldSettingSchema,
  factions: z.array(FactionSchema),
  locations: z.array(WorldLocationSchema),
  events: z.array(HistoryEventSchema),
  generation_summary: z.string(),
});

export type CharacterSummary = z.infer<typeof CharacterSummarySchema>;
export type CharacterDetail = z.infer<typeof CharacterDetailSchema>;
export type CharacterMemory = z.infer<typeof CharacterMemorySchema>;
export type CreateCharacterInput = z.infer<typeof WorkspaceCharacterCreateSchema>;
export type UpdateCharacterInput = z.infer<typeof WorkspaceCharacterUpdateSchema>;
export type OrchestrationStartRequest = z.infer<typeof OrchestrationStartRequestSchema>;
export type OrchestrationStatus = z.infer<typeof OrchestrationStatusSchema>;
export type CharacterGenerationRequest = z.infer<
  typeof CharacterGenerationRequestSchema
>;
export type CharacterGenerationResponse = z.infer<
  typeof CharacterGenerationResponseSchema
>;
export type CharacterProfileGenerationRequest = z.infer<
  typeof CharacterProfileGenerationRequestSchema
>;
export type CharacterProfileGenerationResponse = z.infer<
  typeof CharacterProfileGenerationResponseSchema
>;
export type AuthUser = z.infer<typeof AuthUserSchema>;
export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type AuthResponse = z.infer<typeof AuthResponseSchema>;
export type AuthToken = z.infer<typeof AuthTokenSchema>;
export type GuestSessionResponse = z.infer<typeof GuestSessionResponseSchema>;
export type Campaign = z.infer<typeof CampaignSchema>;
export type SceneGenerationRequest = z.infer<typeof SceneGenerationRequestSchema>;
export type SceneGenerationResponse = z.infer<typeof SceneGenerationResponseSchema>;
export type WorldGenerationRequest = z.infer<typeof WorldGenerationRequestSchema>;
export type WorldGenerationResponse = z.infer<typeof WorldGenerationResponseSchema>;
export type WorldSetting = z.infer<typeof WorldSettingSchema>;
export type Faction = z.infer<typeof FactionSchema>;
export type WorldLocation = z.infer<typeof WorldLocationSchema>;
export type HistoryEvent = z.infer<typeof HistoryEventSchema>;

// === Relationship Schemas (aligned with backend schemas.py) ===

/**
 * Entity types that can participate in relationships.
 */
export const EntityTypeSchema = z.enum([
  'character',
  'faction',
  'location',
  'item',
  'event',
]);

/**
 * Relationship types between entities.
 */
export const RelationshipTypeSchema = z.enum([
  'family',
  'enemy',
  'ally',
  'mentor',
  'romantic',
  'rival',
  'member_of',
  'located_in',
  'owns',
  'created',
  'historical',
  'neutral',
]);

/**
 * Interaction log schema for relationship history.
 */
export const InteractionLogSchema = z.object({
  interaction_id: z.string(),
  summary: z.string(),
  trust_change: z.number().min(-100).max(100),
  romance_change: z.number().min(-100).max(100),
  timestamp: z.string(),
});

/**
 * Relationship response schema matching backend RelationshipResponse.
 */
export const RelationshipResponseSchema = z.object({
  id: z.string(),
  source_id: z.string(),
  source_type: EntityTypeSchema,
  target_id: z.string(),
  target_type: EntityTypeSchema,
  relationship_type: RelationshipTypeSchema,
  description: z.string(),
  strength: z.number().min(0).max(100),
  is_active: z.boolean(),
  trust: z.number().min(0).max(100).default(50),
  romance: z.number().min(0).max(100).default(0),
  interaction_history: z.array(InteractionLogSchema).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Relationship list response schema.
 */
export const RelationshipListResponseSchema = z.object({
  relationships: z.array(RelationshipResponseSchema).default([]),
  total: z.number().default(0),
});

export type EntityType = z.infer<typeof EntityTypeSchema>;
export type RelationshipType = z.infer<typeof RelationshipTypeSchema>;
export type InteractionLog = z.infer<typeof InteractionLogSchema>;
export type RelationshipResponse = z.infer<typeof RelationshipResponseSchema>;
export type RelationshipListResponse = z.infer<typeof RelationshipListResponseSchema>;

/**
 * Error information matching backend's ErrorInfo dataclass
 */
export const ErrorInfoSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.string(), z.unknown()).nullable().optional(),
  recoverable: z.boolean().default(true),
  standard_guidance: z.string().nullable().optional(),
});

export type ErrorInfo = z.infer<typeof ErrorInfoSchema>;

// === Item Schemas (WORLD-008) ===

/**
 * Item type enum matching backend ItemType.
 */
export const ItemTypeEnum = z.enum([
  'weapon',
  'armor',
  'consumable',
  'key_item',
  'misc',
]);

/**
 * Item rarity enum matching backend ItemRarity.
 */
export const ItemRarityEnum = z.enum(['common', 'uncommon', 'rare', 'legendary']);

/**
 * Item response schema matching backend ItemResponse.
 */
export const ItemResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  item_type: ItemTypeEnum,
  description: z.string(),
  rarity: ItemRarityEnum,
  weight: z.number().nullable().optional(),
  value: z.number().nullable().optional(),
  is_equippable: z.boolean(),
  is_consumable: z.boolean(),
  effects: z.array(z.string()).default([]),
  lore: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Item list response schema matching backend ItemListResponse.
 */
export const ItemListResponseSchema = z.object({
  items: z.array(ItemResponseSchema).default([]),
  total: z.number().default(0),
});

/**
 * Give item request schema.
 */
export const GiveItemRequestSchema = z.object({
  item_id: z.string(),
});

/**
 * Remove item response schema.
 */
export const RemoveItemResponseSchema = z.object({
  success: z.boolean(),
  message: z.string(),
});

export type ItemType = z.infer<typeof ItemTypeEnum>;
export type ItemRarity = z.infer<typeof ItemRarityEnum>;
export type ItemResponse = z.infer<typeof ItemResponseSchema>;
export type ItemListResponse = z.infer<typeof ItemListResponseSchema>;
export type GiveItemRequest = z.infer<typeof GiveItemRequestSchema>;
export type RemoveItemResponse = z.infer<typeof RemoveItemResponseSchema>;

// === Narrative Structure Schemas (aligned with backend schemas.py) ===

/**
 * Story response schema matching backend StoryResponse.
 */
export const StoryResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string().default(''),
  status: z.enum(['draft', 'published']),
  chapter_count: z.number().default(0),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Story list response schema matching backend StoryListResponse.
 */
export const StoryListResponseSchema = z.object({
  stories: z.array(StoryResponseSchema).default([]),
});

/**
 * Chapter response schema matching backend ChapterResponse.
 */
export const ChapterResponseSchema = z.object({
  id: z.string(),
  story_id: z.string(),
  title: z.string(),
  summary: z.string().default(''),
  order_index: z.number(),
  status: z.enum(['draft', 'published']),
  scene_count: z.number().default(0),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Chapter list response schema matching backend ChapterListResponse.
 */
export const ChapterListResponseSchema = z.object({
  story_id: z.string(),
  chapters: z.array(ChapterResponseSchema).default([]),
});

/**
 * Story phase enum matching backend StoryPhase.
 * Classifications for narrative structure phases.
 */
export const StoryPhaseEnum = z.enum([
  'setup',              // Introduction, status quo
  'inciting_incident',  // Event that launches the plot
  'rising_action',      // Building tension and complications
  'climax',             // Peak of dramatic tension
  'resolution',         // Aftermath and new status quo
]);

/**
 * Scene response schema matching backend SceneResponse.
 */
export const SceneResponseSchema = z.object({
  id: z.string(),
  chapter_id: z.string(),
  title: z.string(),
  summary: z.string().default(''),
  location: z.string().default(''),
  order_index: z.number(),
  status: z.enum(['draft', 'generating', 'review', 'published']),
  story_phase: StoryPhaseEnum,
  beat_count: z.number().default(0),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Scene list response schema matching backend SceneListResponse.
 */
export const SceneListResponseSchema = z.object({
  chapter_id: z.string(),
  scenes: z.array(SceneResponseSchema).default([]),
});

/**
 * Story create request schema.
 */
export const StoryCreateRequestSchema = z.object({
  title: z.string().min(1).max(200),
  summary: z.string().max(2000).default(''),
});

/**
 * Chapter create request schema.
 */
export const ChapterCreateRequestSchema = z.object({
  title: z.string().min(1).max(200),
  summary: z.string().max(2000).default(''),
  order_index: z.number().int().min(0).optional(),
});

/**
 * Scene create request schema.
 */
export const SceneCreateRequestSchema = z.object({
  title: z.string().min(1).max(200),
  summary: z.string().max(2000).default(''),
  location: z.string().max(500).default(''),
  order_index: z.number().int().min(0).optional(),
});

// Narrative Structure Types
export type StoryResponse = z.infer<typeof StoryResponseSchema>;
export type StoryListResponse = z.infer<typeof StoryListResponseSchema>;
export type ChapterResponse = z.infer<typeof ChapterResponseSchema>;
export type ChapterListResponse = z.infer<typeof ChapterListResponseSchema>;
export type SceneResponse = z.infer<typeof SceneResponseSchema>;
export type SceneListResponse = z.infer<typeof SceneListResponseSchema>;
export type StoryCreateRequest = z.infer<typeof StoryCreateRequestSchema>;
export type ChapterCreateRequest = z.infer<typeof ChapterCreateRequestSchema>;
export type SceneCreateRequest = z.infer<typeof SceneCreateRequestSchema>;
export type StoryPhase = z.infer<typeof StoryPhaseEnum>;

// === Beat Schemas (DIR-042) ===

/**
 * Beat type enum matching backend BeatType.
 * Classifications for narrative beat functions.
 */
export const BeatTypeEnum = z.enum([
  'action',
  'dialogue',
  'reaction',
  'revelation',
  'transition',
  'description',
]);

/**
 * Beat response schema matching backend BeatResponse.
 * Beats are atomic narrative units within a scene.
 */
export const BeatResponseSchema = z.object({
  id: z.string(),
  scene_id: z.string(),
  content: z.string().default(''),
  beat_type: BeatTypeEnum,
  mood_shift: z.number().min(-5).max(5).default(0),
  order_index: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Beat list response schema matching backend BeatListResponse.
 */
export const BeatListResponseSchema = z.object({
  scene_id: z.string(),
  beats: z.array(BeatResponseSchema).default([]),
});

/**
 * Beat create request schema.
 */
export const BeatCreateRequestSchema = z.object({
  content: z.string().max(10000).default(''),
  beat_type: BeatTypeEnum.default('action'),
  mood_shift: z.number().min(-5).max(5).default(0),
  order_index: z.number().int().min(0).optional(),
});

/**
 * Beat update request schema.
 */
export const BeatUpdateRequestSchema = z.object({
  content: z.string().max(10000).optional(),
  beat_type: BeatTypeEnum.optional(),
  mood_shift: z.number().min(-5).max(5).optional(),
});

/**
 * Reorder beats request schema.
 */
export const ReorderBeatsRequestSchema = z.object({
  beat_ids: z.array(z.string()),
});

// === Beat Suggestion Schemas (DIR-047/DIR-048) ===

/**
 * A single AI-generated beat suggestion.
 */
export const BeatSuggestionSchema = z.object({
  beat_type: z.string(),
  content: z.string(),
  mood_shift: z.number().min(-5).max(5).default(0),
  rationale: z.string().optional(),
});

/**
 * Beat suggestion request schema.
 */
export const BeatSuggestionRequestSchema = z.object({
  scene_id: z.string(),
  current_beats: z
    .array(
      z.object({
        beat_type: z.string(),
        content: z.string(),
        mood_shift: z.number().optional(),
      })
    )
    .default([]),
  scene_context: z.string().min(1).max(5000),
  mood_target: z.number().min(-5).max(5).optional(),
});

/**
 * Beat suggestion response schema.
 */
export const BeatSuggestionResponseSchema = z.object({
  scene_id: z.string(),
  suggestions: z.array(BeatSuggestionSchema).min(0).max(3),
  error: z.string().optional(),
});

// Beat Types
export type BeatType = z.infer<typeof BeatTypeEnum>;
export type BeatResponse = z.infer<typeof BeatResponseSchema>;
export type BeatListResponse = z.infer<typeof BeatListResponseSchema>;
export type BeatCreateRequest = z.infer<typeof BeatCreateRequestSchema>;
export type BeatUpdateRequest = z.infer<typeof BeatUpdateRequestSchema>;
export type ReorderBeatsRequest = z.infer<typeof ReorderBeatsRequestSchema>;
export type BeatSuggestion = z.infer<typeof BeatSuggestionSchema>;
export type BeatSuggestionRequest = z.infer<typeof BeatSuggestionRequestSchema>;
export type BeatSuggestionResponse = z.infer<typeof BeatSuggestionResponseSchema>;

// === Pacing Schemas (DIR-043/DIR-044) ===

/**
 * Pacing metrics for a single scene.
 * Used by the PacingGraph to plot tension/energy curves.
 */
export const ScenePacingMetricsSchema = z.object({
  scene_id: z.string(),
  scene_title: z.string(),
  order_index: z.number(),
  tension_level: z.number().min(1).max(10),
  energy_level: z.number().min(1).max(10),
});

/**
 * A detected pacing problem in the chapter.
 */
export const PacingIssueSchema = z.object({
  issue_type: z.string(),
  description: z.string(),
  affected_scenes: z.array(z.string()),
  severity: z.enum(['low', 'medium', 'high']),
  suggestion: z.string(),
});

/**
 * Complete pacing analysis for a chapter.
 * Response from GET /structure/stories/{story_id}/chapters/{chapter_id}/pacing
 */
export const ChapterPacingResponseSchema = z.object({
  chapter_id: z.string(),
  scene_metrics: z.array(ScenePacingMetricsSchema).default([]),
  issues: z.array(PacingIssueSchema).default([]),
  average_tension: z.number(),
  average_energy: z.number(),
  tension_range: z.tuple([z.number(), z.number()]),
  energy_range: z.tuple([z.number(), z.number()]),
});

// Pacing Types
export type ScenePacingMetrics = z.infer<typeof ScenePacingMetricsSchema>;
export type PacingIssue = z.infer<typeof PacingIssueSchema>;
export type ChapterPacingResponse = z.infer<typeof ChapterPacingResponseSchema>;

// === Conflict Schemas (DIR-045) ===

/**
 * Conflict type enum matching backend ConflictType.
 * Classifications for dramatic tension sources.
 */
export const ConflictTypeEnum = z.enum([
  'internal', // Character vs self (moral dilemma, fear, desire)
  'external', // Character vs environment/nature/fate
  'interpersonal', // Character vs character
]);

/**
 * Stakes level enum matching backend ConflictStakes.
 * Indicates how much is at risk in the conflict.
 */
export const ConflictStakesEnum = z.enum([
  'low', // Minor inconvenience, embarrassment
  'medium', // Significant loss, relationship damage
  'high', // Major life impact, severe consequences
  'critical', // Life or death, irreversible change
]);

/**
 * Resolution status enum matching backend ResolutionStatus.
 * Tracks conflict progression through the narrative.
 */
export const ResolutionStatusEnum = z.enum([
  'unresolved', // Conflict is active, no resolution yet
  'escalating', // Conflict is intensifying
  'resolved', // Conflict has been addressed
]);

/**
 * Conflict response schema matching backend ConflictResponse.
 * Conflicts are dramatic tension drivers within a scene.
 */
export const ConflictResponseSchema = z.object({
  id: z.string(),
  scene_id: z.string(),
  conflict_type: ConflictTypeEnum,
  stakes: ConflictStakesEnum,
  description: z.string(),
  resolution_status: ResolutionStatusEnum,
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Conflict list response schema matching backend ConflictListResponse.
 */
export const ConflictListResponseSchema = z.object({
  scene_id: z.string(),
  conflicts: z.array(ConflictResponseSchema).default([]),
});

/**
 * Conflict create request schema.
 */
export const ConflictCreateRequestSchema = z.object({
  conflict_type: ConflictTypeEnum,
  stakes: ConflictStakesEnum.default('medium'),
  description: z.string().min(1).max(2000),
  resolution_status: ResolutionStatusEnum.default('unresolved'),
});

/**
 * Conflict update request schema.
 */
export const ConflictUpdateRequestSchema = z.object({
  conflict_type: ConflictTypeEnum.optional(),
  stakes: ConflictStakesEnum.optional(),
  description: z.string().min(1).max(2000).optional(),
  resolution_status: ResolutionStatusEnum.optional(),
});

// Conflict Types
export type ConflictType = z.infer<typeof ConflictTypeEnum>;
export type ConflictStakes = z.infer<typeof ConflictStakesEnum>;
export type ResolutionStatus = z.infer<typeof ResolutionStatusEnum>;
export type ConflictResponse = z.infer<typeof ConflictResponseSchema>;
export type ConflictListResponse = z.infer<typeof ConflictListResponseSchema>;
export type ConflictCreateRequest = z.infer<typeof ConflictCreateRequestSchema>;
export type ConflictUpdateRequest = z.infer<typeof ConflictUpdateRequestSchema>;

// === Plotline Schemas (DIR-049) ===

/**
 * Plotline status enum matching backend PlotlineStatus.
 * Tracks the lifecycle state of a narrative thread.
 */
export const PlotlineStatusEnum = z.enum([
  'active',     // Currently unfolding in the story
  'resolved',   // Concluded and tied up
  'abandoned',  // Dropped or no longer relevant
]);

/**
 * Plotline response schema matching backend PlotlineResponse.
 *
 * Why: Represents a narrative thread that weaves through multiple scenes.
 * A scene can belong to multiple plotlines simultaneously for complex
 * storytelling (e.g., main plot + subplot + character arc).
 */
export const PlotlineResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  color: z.string().regex(/^#[0-9a-fA-F]{3,8}$/, 'Invalid hex color code'),
  description: z.string(),
  status: PlotlineStatusEnum,
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Plotline list response schema.
 */
export const PlotlineListResponseSchema = z.object({
  plotlines: z.array(PlotlineResponseSchema).default([]),
});

/**
 * Plotline create request schema matching backend PlotlineCreateRequest.
 */
export const PlotlineCreateRequestSchema = z.object({
  name: z.string().min(1).max(200),
  color: z.string().regex(/^#[0-9a-fA-F]{3,8}$/, 'Color must be a valid hex code (e.g., #ff5733)'),
  description: z.string().max(2000).default(''),
  status: PlotlineStatusEnum.default('active'),
});

/**
 * Plotline update request schema matching backend PlotlineUpdateRequest.
 */
export const PlotlineUpdateRequestSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  color: z.string().regex(/^#[0-9a-fA-F]{3,8}$/, 'Color must be a valid hex code').optional(),
  description: z.string().max(2000).optional(),
  status: PlotlineStatusEnum.optional(),
});

/**
 * Link scene to plotline request schema.
 */
export const LinkSceneToPlotlineRequestSchema = z.object({
  plotline_id: z.string(),
});

/**
 * Unlink scene from plotline request schema.
 */
export const UnlinkSceneFromPlotlineRequestSchema = z.object({
  plotline_id: z.string(),
});

/**
 * Set scene plotlines request schema matching backend SetScenePlotlinesRequest.
 *
 * Why: Replaces all plotlines for a scene in a single operation.
 * Used for bulk plotline assignment changes.
 */
export const SetScenePlotlinesRequestSchema = z.object({
  plotline_ids: z.array(z.string()).default([]),
});

/**
 * Scene plotlines response schema matching backend ScenePlotlinesResponse.
 *
 * Why: Returns the list of plotline IDs associated with a scene.
 * The frontend fetches full plotline details separately for display.
 */
export const ScenePlotlinesResponseSchema = z.object({
  scene_id: z.string(),
  plotline_ids: z.array(z.string()).default([]),
});

// Plotline Types
export type PlotlineStatus = z.infer<typeof PlotlineStatusEnum>;
export type PlotlineResponse = z.infer<typeof PlotlineResponseSchema>;
export type PlotlineListResponse = z.infer<typeof PlotlineListResponseSchema>;
export type PlotlineCreateRequest = z.infer<typeof PlotlineCreateRequestSchema>;
export type PlotlineUpdateRequest = z.infer<typeof PlotlineUpdateRequestSchema>;
export type LinkSceneToPlotlineRequest = z.infer<typeof LinkSceneToPlotlineRequestSchema>;
export type UnlinkSceneFromPlotlineRequest = z.infer<typeof UnlinkSceneFromPlotlineRequestSchema>;
export type SetScenePlotlinesRequest = z.infer<typeof SetScenePlotlinesRequestSchema>;
export type ScenePlotlinesResponse = z.infer<typeof ScenePlotlinesResponseSchema>;

// === Foreshadowing Schemas (DIR-052) ===

/**
 * Foreshadowing status enum matching backend ForeshadowingStatus.
 * Tracks the progression from setup to payoff.
 */
export const ForeshadowingStatusEnum = z.enum([
  'planted',    // Setup has been introduced
  'paid_off',   // Payoff has been delivered
  'abandoned',  // Setup was dropped without payoff
]);

/**
 * Foreshadowing response schema matching backend ForeshadowingResponse.
 *
 * Why: Represents Chekhov's Gun - narrative setups that must be paid off.
 * This enforces narrative discipline by tracking all planted threads.
 */
export const ForeshadowingResponseSchema = z.object({
  id: z.string(),
  setup_scene_id: z.string(),
  payoff_scene_id: z.string().nullable(),
  description: z.string(),
  status: ForeshadowingStatusEnum,
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Foreshadowing list response schema.
 */
export const ForeshadowingListResponseSchema = z.object({
  foreshadowings: z.array(ForeshadowingResponseSchema).default([]),
});

/**
 * Foreshadowing create request schema matching backend ForeshadowingCreateRequest.
 */
export const ForeshadowingCreateRequestSchema = z.object({
  setup_scene_id: z.string().min(1, 'Setup scene ID is required'),
  description: z.string().min(1).max(2000, 'Description must be 1-2000 characters'),
  status: ForeshadowingStatusEnum.default('planted'),
});

/**
 * Foreshadowing update request schema matching backend ForeshadowingUpdateRequest.
 */
export const ForeshadowingUpdateRequestSchema = z.object({
  description: z.string().max(2000).optional(),
  status: ForeshadowingStatusEnum.optional(),
  payoff_scene_id: z.string().nullable().optional(),
});

/**
 * Link payoff request schema matching backend LinkPayoffRequest.
 *
 * Why: Separates payoff linking from general updates to validate
 * temporal order (payoff must come after setup).
 */
export const LinkPayoffRequestSchema = z.object({
  payoff_scene_id: z.string().min(1, 'Payoff scene ID is required'),
});

// Foreshadowing Types
export type ForeshadowingStatus = z.infer<typeof ForeshadowingStatusEnum>;
export type ForeshadowingResponse = z.infer<typeof ForeshadowingResponseSchema>;
export type ForeshadowingListResponse = z.infer<typeof ForeshadowingListResponseSchema>;
export type ForeshadowingCreateRequest = z.infer<typeof ForeshadowingCreateRequestSchema>;
export type ForeshadowingUpdateRequest = z.infer<typeof ForeshadowingUpdateRequestSchema>;
export type LinkPayoffRequest = z.infer<typeof LinkPayoffRequestSchema>;

// ============ Chapter Analysis Schemas (DIR-055/DIR-056) ============

/**
 * Health score enum for chapter analysis.
 * CRITICAL: Major structural issues
 * POOR: Multiple significant issues
 * FAIR: Some issues but functional
 * GOOD: Minor issues or well-balanced
 * EXCELLENT: No issues detected
 */
export const HealthScoreEnum = z.enum([
  'critical',
  'poor',
  'fair',
  'good',
  'excellent',
]);

/**
 * Warning category enum for structural issues.
 */
export const WarningCategoryEnum = z.enum([
  'pacing',     // Tension/energy issues
  'structure',  // Phase distribution issues
  'conflict',   // Missing or unresolved conflicts
  'balance',    // Word count and beat count issues
  'arc',        // Tension arc shape issues
]);

/**
 * Phase distribution response schema.
 */
export const PhaseDistributionSchema = z.object({
  setup: z.number().int().min(0),
  inciting_incident: z.number().int().min(0),
  rising_action: z.number().int().min(0),
  climax: z.number().int().min(0),
  resolution: z.number().int().min(0),
});

/**
 * Word count estimate response schema.
 */
export const WordCountEstimateSchema = z.object({
  total_words: z.number().int().min(0),
  min_words: z.number().int().min(0),
  max_words: z.number().int().min(0),
  per_scene_average: z.number(),
});

/**
 * Health warning response schema.
 */
export const HealthWarningSchema = z.object({
  category: z.string(),
  title: z.string(),
  description: z.string(),
  severity: z.enum(['low', 'medium', 'high', 'critical']),
  affected_scenes: z.array(z.string()).default([]),
  recommendation: z.string(),
});

/**
 * Tension arc shape response schema.
 */
export const TensionArcShapeSchema = z.object({
  shape_type: z.string(),
  starts_at: z.number().int().min(0).max(10),
  peaks_at: z.number().int().min(0).max(10),
  ends_at: z.number().int().min(0).max(10),
  has_clear_climax: z.boolean(),
  is_monotonic: z.boolean(),
});

/**
 * Chapter health report response schema.
 */
export const ChapterHealthReportSchema = z.object({
  chapter_id: z.string(),
  health_score: HealthScoreEnum,
  phase_distribution: PhaseDistributionSchema,
  word_count: WordCountEstimateSchema,
  total_scenes: z.number().int().min(0),
  total_beats: z.number().int().min(0),
  tension_arc: TensionArcShapeSchema,
  warnings: z.array(HealthWarningSchema).default([]),
  recommendations: z.array(z.string()).default([]),
});

// Type exports
export type HealthScore = z.infer<typeof HealthScoreEnum>;
export type WarningCategory = z.infer<typeof WarningCategoryEnum>;
export type PhaseDistribution = z.infer<typeof PhaseDistributionSchema>;
export type WordCountEstimate = z.infer<typeof WordCountEstimateSchema>;
export type HealthWarning = z.infer<typeof HealthWarningSchema>;
export type TensionArcShape = z.infer<typeof TensionArcShapeSchema>;
export type ChapterHealthReport = z.infer<typeof ChapterHealthReportSchema>;

/**
 * Standard API response envelope matching backend's StandardResponse
 *
 * This generic type wraps all API responses with consistent metadata
 * for error handling and debugging.
 *
 * @example
 * ```typescript
 * // Success response
 * const response: ApiResponse<Character> = {
 *   success: true,
 *   data: character,
 *   metadata: { request_id: '123' },
 *   timestamp: '2024-01-01T00:00:00Z'
 * };
 *
 * // Error response
 * const errorResponse: ApiResponse<never> = {
 *   success: false,
 *   error: { code: 'NOT_FOUND', message: 'Character not found' },
 *   metadata: {},
 *   timestamp: '2024-01-01T00:00:00Z'
 * };
 * ```
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ErrorInfo;
  metadata: Record<string, unknown>;
  timestamp: string;
}

/**
 * Create a Zod schema for ApiResponse with a given data schema
 */
export function createApiResponseSchema<T extends z.ZodTypeAny>(dataSchema: T) {
  return z.object({
    success: z.boolean(),
    data: dataSchema.optional(),
    error: ErrorInfoSchema.optional(),
    metadata: z.record(z.string(), z.unknown()).default({}),
    timestamp: z.string(),
  });
}

// === Lore Entry Schemas (WORLD-010/WORLD-011) ===

/**
 * Lore category enum matching backend LoreCategory.
 */
export const LoreCategoryEnum = z.enum(['history', 'culture', 'magic', 'technology']);

/**
 * Lore entry response schema matching backend LoreEntryResponse.
 */
export const LoreEntryResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  content: z.string(),
  category: LoreCategoryEnum,
  tags: z.array(z.string()).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * Lore entry list response schema matching backend LoreEntryListResponse.
 */
export const LoreEntryListResponseSchema = z.object({
  entries: z.array(LoreEntryResponseSchema).default([]),
  total: z.number().default(0),
});

/**
 * Lore entry create/update request schema.
 */
export const LoreEntryRequestSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().max(10000),
  category: LoreCategoryEnum,
  tags: z.array(z.string()).default([]),
});

export type LoreCategory = z.infer<typeof LoreCategoryEnum>;
export type LoreEntryResponse = z.infer<typeof LoreEntryResponseSchema>;
export type LoreEntryListResponse = z.infer<typeof LoreEntryListResponseSchema>;
export type LoreEntryRequest = z.infer<typeof LoreEntryRequestSchema>;

// === World Rule Schemas (WORLD-014/WORLD-015) ===

/**
 * World rule response schema matching backend WorldRuleResponse.
 */
export const WorldRuleResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  consequence: z.string(),
  exceptions: z.array(z.string()).default([]),
  category: z.string(),
  severity: z.number().min(0).max(100),
  related_rule_ids: z.array(z.string()).default([]),
  created_at: z.string(),
  updated_at: z.string(),
});

/**
 * World rule list response schema matching backend WorldRuleListResponse.
 */
export const WorldRuleListResponseSchema = z.object({
  rules: z.array(WorldRuleResponseSchema).default([]),
  total: z.number().default(0),
});

/**
 * World rule create request schema.
 */
export const WorldRuleCreateRequestSchema = z.object({
  name: z.string().min(1).max(200),
  description: z.string().max(5000).default(''),
  consequence: z.string().max(2000).default(''),
  exceptions: z.array(z.string()).max(20).default([]),
  category: z.string().max(50).default(''),
  severity: z.number().min(0).max(100).default(50),
});

/**
 * World rule update request schema.
 */
export const WorldRuleUpdateRequestSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  description: z.string().max(5000).optional(),
  consequence: z.string().max(2000).optional(),
  exceptions: z.array(z.string()).max(20).optional(),
  category: z.string().max(50).optional(),
  severity: z.number().min(0).max(100).optional(),
});

export type WorldRuleResponse = z.infer<typeof WorldRuleResponseSchema>;
export type WorldRuleListResponse = z.infer<typeof WorldRuleListResponseSchema>;
export type WorldRuleCreateRequest = z.infer<typeof WorldRuleCreateRequestSchema>;
export type WorldRuleUpdateRequest = z.infer<typeof WorldRuleUpdateRequestSchema>;

// === Dialogue Generation Schemas (CHAR-027/CHAR-028) ===

/**
 * Request for generating character dialogue.
 * Uses character psychology, traits, and speaking style to generate
 * authentic dialogue that sounds like the character would naturally speak.
 */
export const DialogueGenerationRequestSchema = z.object({
  character_id: z.string(),
  context: z.string().min(1).max(1000),
  mood: z.string().max(50).optional(),
  psychology_override: CharacterPsychologySchema.optional(),
  traits_override: z.array(z.string()).optional(),
  speaking_style_override: z.string().max(200).optional(),
});

/**
 * Response from dialogue generation.
 * Contains the character's spoken words along with metadata about
 * their internal state and physical expression.
 */
export const DialogueGenerationResponseSchema = z.object({
  dialogue: z.string(),
  tone: z.string(),
  internal_thought: z.string().nullable().optional(),
  body_language: z.string().nullable().optional(),
  character_id: z.string(),
  error: z.string().nullable().optional(),
});

export type DialogueGenerationRequest = z.infer<typeof DialogueGenerationRequestSchema>;
export type DialogueGenerationResponse = z.infer<
  typeof DialogueGenerationResponseSchema
>;

// === Character Goal Schemas (CHAR-029/CHAR-030) ===

/**
 * Goal status enum matching backend GoalStatus.
 * - ACTIVE: Currently being pursued
 * - COMPLETED: Successfully achieved
 * - FAILED: Abandoned or became impossible
 */
export const GoalStatusEnum = z.enum(['ACTIVE', 'COMPLETED', 'FAILED']);

/**
 * Goal urgency enum matching backend GoalUrgency.
 * - LOW: Background ambition, no time pressure
 * - MEDIUM: Important but not immediate
 * - HIGH: Pressing concern that demands attention
 * - CRITICAL: Must be addressed immediately
 */
export const GoalUrgencyEnum = z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);

/**
 * Character goal schema matching backend CharacterGoalSchema.
 */
export const CharacterGoalSchema = z.object({
  goal_id: z.string(),
  description: z.string().min(1),
  status: GoalStatusEnum,
  urgency: GoalUrgencyEnum,
  created_at: z.string(),
  completed_at: z.string().nullable().optional(),
  is_active: z.boolean(),
  is_urgent: z.boolean(),
});

/**
 * Character goals response schema matching backend CharacterGoalsResponse.
 */
export const CharacterGoalsResponseSchema = z.object({
  character_id: z.string(),
  goals: z.array(CharacterGoalSchema),
  total_count: z.number(),
  active_count: z.number(),
  completed_count: z.number(),
  failed_count: z.number(),
});

/**
 * Request to create a new goal.
 */
export const CharacterGoalCreateRequestSchema = z.object({
  description: z.string().min(1),
  urgency: GoalUrgencyEnum.optional().default('MEDIUM'),
});

/**
 * Request to update a goal's status or urgency.
 */
export const CharacterGoalUpdateRequestSchema = z.object({
  status: GoalStatusEnum.optional(),
  urgency: GoalUrgencyEnum.optional(),
});

export type GoalStatus = z.infer<typeof GoalStatusEnum>;
export type GoalUrgency = z.infer<typeof GoalUrgencyEnum>;
export type CharacterGoal = z.infer<typeof CharacterGoalSchema>;
export type CharacterGoalsResponse = z.infer<typeof CharacterGoalsResponseSchema>;
export type CharacterGoalCreateRequest = z.infer<
  typeof CharacterGoalCreateRequestSchema
>;
export type CharacterGoalUpdateRequest = z.infer<
  typeof CharacterGoalUpdateRequestSchema
>;

// === Social Network Analysis Schemas (CHAR-031/CHAR-032) ===

/**
 * Centrality metrics for a single character in the social network.
 * Used to identify key characters based on their relationship patterns.
 */
export const CharacterCentralitySchema = z.object({
  character_id: z.string(),
  relationship_count: z.number().int().min(0),
  positive_count: z.number().int().min(0),
  negative_count: z.number().int().min(0),
  average_trust: z.number().min(0).max(100),
  average_romance: z.number().min(0).max(100),
  centrality_score: z.number().min(0).max(100),
});

/**
 * Complete social network analysis result.
 * Provides graph analytics for the character relationship network.
 */
export const SocialAnalysisResponseSchema = z.object({
  character_centralities: z.record(z.string(), CharacterCentralitySchema),
  most_connected: z.string().nullable().optional(),
  most_hated: z.string().nullable().optional(),
  most_loved: z.string().nullable().optional(),
  total_relationships: z.number().int().min(0),
  total_characters: z.number().int().min(0),
  network_density: z.number().min(0).max(1),
});

export type CharacterCentrality = z.infer<typeof CharacterCentralitySchema>;
export type SocialAnalysisResponse = z.infer<typeof SocialAnalysisResponseSchema>;

// === Relationship History Generation Schemas (CHAR-034) ===

/**
 * Response from relationship history generation.
 * Contains a backstory explaining the relationship dynamics.
 */
export const RelationshipHistoryGenerationResponseSchema = z.object({
  backstory: z.string(),
  first_meeting: z.string().nullable().optional(),
  defining_moment: z.string().nullable().optional(),
  current_status: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
});

export type RelationshipHistoryGenerationResponse = z.infer<
  typeof RelationshipHistoryGenerationResponseSchema
>;

// === Faction Schemas (CHAR-035/CHAR-036) ===

/**
 * Schema for a faction member.
 * Represents a character who belongs to a faction.
 */
export const FactionMemberSchema = z.object({
  character_id: z.string(),
  name: z.string().default(''),
  is_leader: z.boolean().default(false),
});

/**
 * Faction type enum matching backend FactionType.
 */
export const FactionTypeEnum = z.enum([
  'kingdom',
  'empire',
  'guild',
  'cult',
  'corporation',
  'military',
  'religious',
  'criminal',
  'academic',
  'merchant',
  'tribal',
  'revolutionary',
  'secret_society',
  'adventurer_group',
  'noble_house',
]);

/**
 * Faction alignment enum matching backend FactionAlignment.
 */
export const FactionAlignmentEnum = z.enum([
  'lawful_good',
  'neutral_good',
  'chaotic_good',
  'lawful_neutral',
  'true_neutral',
  'chaotic_neutral',
  'lawful_evil',
  'neutral_evil',
  'chaotic_evil',
]);

/**
 * Faction status enum matching backend FactionStatus.
 */
export const FactionStatusEnum = z.enum([
  'active',
  'dormant',
  'disbanded',
  'emerging',
  'declining',
  'conquered',
  'hidden',
]);

/**
 * Faction detail response schema matching backend FactionDetailResponse.
 * Includes faction metadata and list of members.
 */
export const FactionDetailResponseSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().default(''),
  faction_type: z.string(),
  alignment: z.string(),
  status: z.string(),
  leader_id: z.string().nullable().optional(),
  leader_name: z.string().nullable().optional(),
  influence: z.number().min(0).max(100).default(50),
  member_count: z.number().int().min(0).default(0),
  members: z.array(FactionMemberSchema).default([]),
});

export type FactionMember = z.infer<typeof FactionMemberSchema>;
export type FactionType = z.infer<typeof FactionTypeEnum>;
export type FactionAlignment = z.infer<typeof FactionAlignmentEnum>;
export type FactionStatus = z.infer<typeof FactionStatusEnum>;
export type FactionDetailResponse = z.infer<typeof FactionDetailResponseSchema>;
