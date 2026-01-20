/**
 * Character Types
 */

export interface Character {
  id: string;
  name: string;
  description: string;
  role: CharacterRole;
  traits: string[];
  stats: CharacterStats;
  relationships: CharacterRelationship[];
  imageUrl?: string;
  createdAt: string;
  updatedAt: string;
}

export type CharacterRole = 'protagonist' | 'antagonist' | 'supporting' | 'minor' | 'npc';

export interface CharacterStats {
  strength: number;
  intelligence: number;
  charisma: number;
  agility: number;
  wisdom: number;
  luck: number;
}

export interface CharacterRelationship {
  targetId: string;
  targetName: string;
  type: RelationshipType;
  strength: number; // -100 to 100
  description?: string;
}

export type RelationshipType = 'ally' | 'enemy' | 'neutral' | 'family' | 'romantic' | 'rival';

export interface CreateCharacterInput {
  name: string;
  description: string;
  role: CharacterRole;
  traits?: string[];
  stats?: Partial<CharacterStats>;
}

export interface UpdateCharacterInput extends Partial<CreateCharacterInput> {
  id: string;
}
