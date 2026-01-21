import { z } from 'zod';
import {
  CharacterSummarySchema,
  CharacterDetailSchema,
  WorkspaceCharacterCreateSchema,
  WorkspaceCharacterUpdateSchema,
} from '@/types/schemas';

export type CharacterSummary = z.infer<typeof CharacterSummarySchema>;
export type CharacterDetail = z.infer<typeof CharacterDetailSchema>;
export type CreateCharacterInput = z.infer<typeof WorkspaceCharacterCreateSchema>;
export type UpdateCharacterInput = z.infer<typeof WorkspaceCharacterUpdateSchema>;
