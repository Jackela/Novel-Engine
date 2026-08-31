import {
  DEFAULT_LORE_STATUS,
  INJECTABLE_LORE_STATUS,
  isLoreStatus,
  type LoreStatus,
} from "../domain/kinds.js";
import type { ProjectScope, StudioStore } from "./ports/studio_store.js";
import { LOREBOOK_BEGIN, LOREBOOK_END } from "./sanitization.js";

/**
 * Keyword-triggered lorebook (#315, ADR-0004 layer 2): character and world
 * documents are lore entries. Keys are the document title plus its declared
 * aliases; content is the document's current markdown. An entry is injected
 * only when it is `stable` (#444, ADR-0006) and one of its keys occurs in
 * the resident context or the target manuscript, and matched entries render
 * in their documents' reading order.
 */

/** The document kinds that serve as lore entries. */
export const LOREBOOK_ENTRY_KINDS = ["character", "world"] as const;

export function isLoreEntryKind(kind: string): boolean {
  return (LOREBOOK_ENTRY_KINDS as readonly string[]).includes(kind);
}

/**
 * Narrow a stored lifecycle value to the closed enum, fail-closed (#444):
 * anything unreadable reads as `draft`, so an unknown or corrupted value can
 * never promote an entry into the prompt. Like alias parsing this is defined
 * gating semantics for advisory stored state, not swallowed errors — write
 * paths validate the enum strictly before it ever reaches a row.
 */
export function asLoreStatus(value: string): LoreStatus {
  return isLoreStatus(value) ? value : DEFAULT_LORE_STATUS;
}

/** The minimal entry facts; document rows satisfy this shape directly. */
export interface LoreEntrySource {
  readonly title: string;
  /** Stored alias JSON (a `string[]` column value); parsed defensively on read. */
  readonly loreAliasesJson: string;
  /** The entry's lifecycle status; only `stable` entries are injectable (#444). */
  readonly status: LoreStatus;
  readonly contentMarkdown: string | null;
}

export interface LoreMatchCorpora {
  readonly resident: string;
  readonly manuscript: string;
}

/** Upper bound on stored aliases per document (request schemas mirror it). */
export const MAX_LORE_ALIASES = 64;
const MAX_LORE_ALIAS_LENGTH = 240;

/** Parse stored alias JSON defensively: anything but a string array reads as no aliases. */
export function parseLoreAliases(loreAliasesJson: string): string[] {
  try {
    const parsed: unknown = JSON.parse(loreAliasesJson);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((value): value is string => typeof value === "string");
  } catch {
    // Stored aliases are advisory prompt keys; a malformed value must not
    // take down prompt assembly or reads.
    return [];
  }
}

/**
 * Write-path normalization (#315 API contract): trim every alias, drop
 * blanks and overlong entries, dedupe case-insensitively while keeping the
 * first spelling, and cap the list at the schema limit.
 */
export function normalizeLoreAliases(values: readonly string[]): string[] {
  const normalized: string[] = [];
  for (const candidate of values.slice(0, MAX_LORE_ALIASES * 2)) {
    const alias = String(candidate).trim().slice(0, MAX_LORE_ALIAS_LENGTH);
    if (alias === "" || normalized.some((kept) => kept.toLowerCase() === alias.toLowerCase())) {
      continue;
    }
    normalized.push(alias);
    if (normalized.length >= MAX_LORE_ALIASES) {
      break;
    }
  }
  return normalized;
}

/** The effective keys of an entry: the trimmed title plus trimmed non-blank aliases. */
export function loreEntryKeys(entry: LoreEntrySource): string[] {
  const keys = [
    entry.title.trim(),
    ...parseLoreAliases(entry.loreAliasesJson).map((alias) => alias.trim()),
  ];
  return keys.filter((key) => key !== "");
}

function hasInjectableContent(entry: LoreEntrySource): boolean {
  return entry.contentMarkdown !== null && entry.contentMarkdown.trim() !== "";
}

/**
 * Selection semantics (#315, #444, documented): keys match by case-insensitive
 * SUBSTRING occurrence over either corpus — whole-token boundaries are
 * deliberately not required, so names embedded in larger words still
 * trigger. Entries without injectable content never render, and the
 * lifecycle gate (#444, ADR-0006) admits only `stable` entries: a `draft`
 * keeps half-written documents out of the prompt even when their title is
 * mentioned, and `deprecated` retires an entry without deleting it. No
 * downweighting — the gate is binary by adjudication.
 */
export function matchLoreEntries(
  entries: readonly LoreEntrySource[],
  corpora: LoreMatchCorpora,
): LoreEntrySource[] {
  const haystack = `${corpora.resident}\n${corpora.manuscript}`.toLowerCase();
  const matched: LoreEntrySource[] = [];
  for (const entry of entries) {
    // Lifecycle gate first (ADR-0006): non-stable entries are skipped before
    // any key evaluation.
    if (entry.status !== INJECTABLE_LORE_STATUS) {
      continue;
    }
    if (!hasInjectableContent(entry)) {
      continue;
    }
    const hit = loreEntryKeys(entry).some((key) => haystack.includes(key.toLowerCase()));
    if (hit) {
      matched.push(entry);
    }
  }
  return matched;
}

/** One trusted-context line block per entry: a heading plus the raw markdown body. */
export function renderLoreSection(matched: readonly LoreEntrySource[]): string[] {
  if (matched.length === 0) {
    return [];
  }
  const sections: string[] = [
    "",
    "LOREBOOK (reference entries triggered by their keys occurring above):",
    LOREBOOK_BEGIN,
  ];
  for (const entry of matched) {
    // Headings stay single-line so each `###` reliably opens exactly one entry.
    sections.push(
      `### ${entry.title.replace(/\s+/g, " ").trim()}`,
      "",
      entry.contentMarkdown?.trim() ?? "",
      "",
    );
  }
  sections.push(LOREBOOK_END);
  return sections;
}

/** Match then render in one step; an empty result renders no section at all. */
export function triggeredLoreSections(
  input: {
    entries: readonly LoreEntrySource[];
  } & LoreMatchCorpora,
): string[] {
  return renderLoreSection(
    matchLoreEntries(input.entries, { resident: input.resident, manuscript: input.manuscript }),
  );
}

/**
 * Gather lore entries from the project's own character/world documents in the
 * store's composite reading order — the same order the resident assembler and
 * every project listing use, which pins injection order deterministically.
 */
export function collectLoreEntries(
  store: StudioStore,
  scope: ProjectScope,
  projectId: string,
): LoreEntrySource[] {
  return store
    .findDocuments(scope, projectId)
    .filter((document) => isLoreEntryKind(document.kind))
    .map((document) => ({
      title: document.title,
      loreAliasesJson: document.loreAliasesJson,
      // Store rows carry write-validated enum values; the gate narrows
      // fail-closed so an unknown stored value reads as non-injectable.
      status: asLoreStatus(document.loreStatus),
      contentMarkdown: document.currentRevision?.contentMarkdown ?? null,
    }));
}
