import { BookOpen, FileText, Globe2, Users } from "lucide-react";

import type { DocumentKind, ProviderInfo } from "@/app/types/studio";

export const GROUPS: Array<{
  kind: DocumentKind;
  label: string;
  icon: typeof FileText;
}> = [
  { kind: "chapter", label: "Manuscript", icon: BookOpen },
  { kind: "outline", label: "Outline", icon: FileText },
  { kind: "character", label: "Characters", icon: Users },
  { kind: "world", label: "World", icon: Globe2 },
  { kind: "note", label: "Notes", icon: FileText },
];

/**
 * Inspector selection is URL-owned. Review, history, and export use project
 * paths; Copilot, jobs, and usage use the authoring route query.
 */
export type InspectorTab =
  | "copilot"
  | "review"
  | "history"
  | "export"
  | "jobs"
  | "usage"
  | "settings";

export const INSPECTOR_TABS: Exclude<InspectorTab, "settings">[] = [
  "copilot",
  "review",
  "history",
  "export",
  "jobs",
  "usage",
];

export const SECTIONS = [
  ["manuscript", "Manuscript"],
  ["outline", "Outline"],
  ["characters", "Characters"],
  ["world", "World"],
  ["settings", "Settings"],
] as const;

/** The document kinds that serve as lorebook entries (#315); lifecycle-gated (#444). */
export const LOREBOOK_ENTRY_KINDS: readonly DocumentKind[] = ["character", "world"];

export function isLoreEntryKind(kind: DocumentKind): boolean {
  return LOREBOOK_ENTRY_KINDS.includes(kind);
}

export const DEFAULT_PROVIDER_OPTIONS: ProviderInfo[] = [
  { provider: "mock", configured: true, model: null, is_default: true },
  { provider: "dashscope", configured: false, model: null, is_default: false },
  {
    provider: "openai_compatible",
    configured: false,
    model: null,
    is_default: false,
  },
];
