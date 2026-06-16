import { BookOpen, FileText, Globe2, Users } from 'lucide-react';

import type { DocumentKind } from '@/app/types/studio';

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
