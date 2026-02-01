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
export const ItemTypeEnum = z.enum(['weapon', 'armor', 'consumable', 'key_item', 'misc']);

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
export type DialogueGenerationResponse = z.infer<typeof DialogueGenerationResponseSchema>;

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
export type CharacterGoalCreateRequest = z.infer<typeof CharacterGoalCreateRequestSchema>;
export type CharacterGoalUpdateRequest = z.infer<typeof CharacterGoalUpdateRequestSchema>;
