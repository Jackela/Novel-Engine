import { z } from 'zod';

export const CharacterRoleSchema = z.enum([
  'protagonist',
  'antagonist',
  'supporting',
  'minor',
  'npc',
]);

export const CharacterStatsSchema = z.object({
  strength: z.number(),
  intelligence: z.number(),
  charisma: z.number(),
  agility: z.number(),
  wisdom: z.number(),
  luck: z.number(),
});

export const CharacterRelationshipSchema = z.object({
  targetId: z.string(),
  targetName: z.string(),
  type: z.enum(['ally', 'enemy', 'neutral', 'family', 'romantic', 'rival']),
  strength: z.number(),
  description: z.string().optional(),
});

export const CharacterSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  role: CharacterRoleSchema,
  traits: z.array(z.string()),
  stats: CharacterStatsSchema,
  relationships: z.array(CharacterRelationshipSchema),
  imageUrl: z.string().optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
});

export const CharactersResponseSchema = z.array(CharacterSchema);

export const CreateCharacterInputSchema = z.object({
  name: z.string(),
  description: z.string(),
  role: CharacterRoleSchema,
  traits: z.array(z.string()).optional(),
  stats: CharacterStatsSchema.partial().optional(),
});

export const UpdateCharacterInputSchema = CreateCharacterInputSchema.partial().extend({
  id: z.string(),
});

export const OrchestrationStartRequestSchema = z.object({
  character_names: z.array(z.string().min(1)).min(2).max(6),
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

export type Character = z.infer<typeof CharacterSchema>;
export type CharacterRole = z.infer<typeof CharacterRoleSchema>;
export type CharacterStats = z.infer<typeof CharacterStatsSchema>;
export type CharacterRelationship = z.infer<typeof CharacterRelationshipSchema>;
export type CreateCharacterInput = z.infer<typeof CreateCharacterInputSchema>;
export type UpdateCharacterInput = z.infer<typeof UpdateCharacterInputSchema>;
export type OrchestrationStartRequest = z.infer<typeof OrchestrationStartRequestSchema>;
export type OrchestrationStatus = z.infer<typeof OrchestrationStatusSchema>;
