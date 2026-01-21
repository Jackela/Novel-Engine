import { z } from 'zod';
import {
  CharacterSchema,
  CharacterRoleSchema,
  CharacterStatsSchema,
  CharacterRelationshipSchema,
  CreateCharacterInputSchema,
  UpdateCharacterInputSchema,
} from '@/types/schemas';

export type Character = z.infer<typeof CharacterSchema>;
export type CharacterRole = z.infer<typeof CharacterRoleSchema>;
export type CharacterStats = z.infer<typeof CharacterStatsSchema>;
export type CharacterRelationship = z.infer<typeof CharacterRelationshipSchema>;
export type RelationshipType = CharacterRelationship['type'];
export type CreateCharacterInput = z.infer<typeof CreateCharacterInputSchema>;
export type UpdateCharacterInput = z.infer<typeof UpdateCharacterInputSchema>;
