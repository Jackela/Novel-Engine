import { BookOpen, FileText, Globe2, Users } from 'lucide-react';

import type { DocumentKind, ProviderInfo } from '@/app/types/studio';

export const GROUPS: Array<{
  kind: DocumentKind;
  label: string;
  icon: typeof FileText;
}> = [
  { kind: 'chapter', label: 'Manuscript', icon: BookOpen },
  { kind: 'outline', label: 'Outline', icon: FileText },
  { kind: 'character', label: 'Characters', icon: Users },
  { kind: 'world', label: 'World', icon: Globe2 },
  { kind: 'note', label: 'Notes', icon: FileText },
];

export type InspectorTab = 'copilot' | 'review' | 'history' | 'jobs' | 'settings';

export const SECTIONS = [
  ['manuscript', 'Manuscript'],
  ['outline', 'Outline'],
  ['characters', 'Characters'],
  ['world', 'World'],
  ['review', 'Review'],
  ['history', 'History'],
  ['export', 'Export'],
  ['settings', 'Settings'],
] as const;

export const DEFAULT_PROVIDER_OPTIONS: ProviderInfo[] = [
  { provider: 'mock', configured: true, model: null, is_default: true },
  { provider: 'dashscope', configured: false, model: null, is_default: false },
  { provider: 'openai_compatible', configured: false, model: null, is_default: false },
];
