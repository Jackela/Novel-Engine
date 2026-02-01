import { z } from 'zod';

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

export const WorldLocationSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  location_type: z.string(),
  population: z.number(),
  controlling_faction_id: z.string().nullable(),
  notable_features: z.array(z.string()),
  danger_level: z.string(),
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
