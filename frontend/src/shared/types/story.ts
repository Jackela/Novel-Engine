/**
 * Story Types
 */

export interface Story {
  id: string;
  title: string;
  content: string;
  summary?: string;
  campaignId: string;
  turnNumber: number;
  characters: string[];
  events: StoryEvent[];
  mood: StoryMood;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export type StoryMood = 'tense' | 'calm' | 'dramatic' | 'mysterious' | 'action' | 'emotional';

export interface StoryEvent {
  id: string;
  type: StoryEventType;
  description: string;
  involvedCharacters: string[];
  timestamp: string;
}

export type StoryEventType =
  | 'dialogue'
  | 'action'
  | 'discovery'
  | 'conflict'
  | 'resolution'
  | 'transition';

export interface GenerateStoryInput {
  campaignId: string;
  prompt?: string;
  characters?: string[];
  mood?: StoryMood;
}

export interface StoryGenerationProgress {
  taskId: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  progress: number;
  currentStep?: string;
  result?: Story;
  error?: string;
}
