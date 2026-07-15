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

/**
 * Inspector routes are intentionally independent from the project-level
 * section routes.  In particular, export is its own panel rather than an
 * alias for history so that the two workflows remain discoverable and
 * keyboard addressable.
 */
export type InspectorTab = 'copilot' | 'review' | 'history' | 'export' | 'jobs' | 'settings';

export const INSPECTOR_TABS: Exclude<InspectorTab, 'settings'>[] = [
  'copilot',
  'review',
  'history',
  'export',
  'jobs',
];

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
