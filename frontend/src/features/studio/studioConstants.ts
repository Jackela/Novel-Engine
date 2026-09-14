import { BookOpen, FileText, Globe2, Users } from "lucide-react";

import type { MessageKey } from "@/app/i18n/dictionaries/en";
import { translateActive } from "@/app/i18n/translate";
import type { DocumentKind, ProviderInfo } from "@/app/types/studio";

/**
 * `label` is the language-independent content name used when *creating*
 * documents ("Characters 2" as stored data, see `useStudioDocumentActions`);
 * `messageKey` is the UI chrome label, resolved through the dictionaries so
 * the Navigator follows the active UI language.
 */
export const GROUPS: Array<{
  kind: DocumentKind;
  label: string;
  messageKey: MessageKey;
  icon: typeof FileText;
}> = [
  {
    kind: "chapter",
    label: "Manuscript",
    messageKey: "navigator.group.manuscript",
    icon: BookOpen,
  },
  { kind: "outline", label: "Outline", messageKey: "navigator.group.outline", icon: FileText },
  {
    kind: "character",
    label: "Characters",
    messageKey: "navigator.group.characters",
    icon: Users,
  },
  { kind: "world", label: "World", messageKey: "navigator.group.world", icon: Globe2 },
  { kind: "note", label: "Notes", messageKey: "navigator.group.notes", icon: FileText },
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

/**
 * Section display labels resolve through the dictionaries; the first tuple
 * element stays the URL-owned route segment.
 */
export const SECTIONS = [
  ["manuscript", "navigator.section.manuscript"],
  ["outline", "navigator.section.outline"],
  ["characters", "navigator.section.characters"],
  ["world", "navigator.section.world"],
  ["settings", "navigator.section.settings"],
] as const satisfies readonly (readonly [string, MessageKey])[];

/** The document kinds that serve as lorebook entries (#315); lifecycle-gated (#444). */
const LOREBOOK_ENTRY_KINDS: readonly DocumentKind[] = ["character", "world"];

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

/**
 * Display-only labels for the raw provider IDs surfaced by the API (#606),
 * resolved through the i18n dictionaries (`provider.*` family) so the
 * settings panel follows the active UI language. Unknown IDs fall back to
 * their raw value so providers added server-side later remain visible and
 * selectable without a frontend change.
 *
 * Reactivity note: the lookup reads the active language at call time, so
 * labels refresh in any component that re-renders on a language switch
 * (via `useTranslation`). Panels not yet wired to the hook keep rendering
 * the last-resolved language until their phase-2 conversion.
 */
const PROVIDER_MESSAGE_KEYS: Record<string, MessageKey> = {
  mock: "provider.mock",
  dashscope: "provider.dashscope",
  openai_compatible: "provider.openaiCompatible",
};

export function providerLabel(provider: string): string {
  const key = PROVIDER_MESSAGE_KEYS[provider];
  return key ? translateActive(key) : provider;
}
