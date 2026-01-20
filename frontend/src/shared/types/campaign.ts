/**
 * Campaign Types
 */

export interface Campaign {
  id: string;
  name: string;
  description: string;
  status: CampaignStatus;
  worldId?: string;
  characterIds: string[];
  currentTurn: number;
  settings: CampaignSettings;
  createdAt: string;
  updatedAt: string;
}

export type CampaignStatus = 'draft' | 'active' | 'paused' | 'completed' | 'archived';

export interface CampaignSettings {
  maxTurns?: number;
  autoAdvance: boolean;
  narrativeStyle: 'descriptive' | 'cinematic' | 'dialogue-heavy' | 'action-focused';
  complexity: 'simple' | 'moderate' | 'complex';
}

export interface CreateCampaignInput {
  name: string;
  description: string;
  characterIds?: string[];
  settings?: Partial<CampaignSettings>;
}

export interface UpdateCampaignInput extends Partial<CreateCampaignInput> {
  id: string;
  status?: CampaignStatus;
}
