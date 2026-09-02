import type { LoreEntrySource, LoreMatch, LoreMatchRank } from "./lorebook.js";
import { type LoreMatchCorpora, loreEntrySummary, matchLoreEntriesWithRank } from "./lorebook.js";
import { escapePromptData, LOREBOOK_BEGIN, LOREBOOK_END } from "./sanitization.js";

/**
 * Progressive disclosure under the lorebook injection budget (#445, ADR-0006):
 * every matched entry enters the prompt as one summary line, then entries are
 * promoted to full text greedily — title hits before alias hits, ties in
 * reading order — while the rendered lorebook section fits the character
 * budget. Over-budget hits keep their summary line; nothing is silently
 * dropped. The plan is a pure function of the match list and the budget, so
 * repeated runs render byte-identically.
 */

/**
 * The default character budget of the rendered lorebook section (#445). The
 * server config seam mirrors this value (provider_config.ts); shared never
 * imports bounded contexts, so the two constants are kept in step
 * deliberately. Rationale lives in ADR-0006.
 */
export const DEFAULT_LOREBOOK_BUDGET_CHARACTERS = 4000;

/** How much of an entry the prompt carries: the whole body or one summary line. */
export type LoreInjectionMode = "full" | "summary";

export interface PlannedLoreInjection {
  readonly entry: LoreEntrySource;
  readonly mode: LoreInjectionMode;
}

const LOREBOOK_SECTION_HEADER =
  "LOREBOOK (reference entries triggered by their keys occurring above):";

interface PreparedLoreInjection {
  readonly entry: LoreEntrySource;
  readonly rank: LoreMatchRank;
  readonly summaryLines: readonly [string, "", string, ""];
  readonly fullLines: readonly [string, "", string, ""];
  readonly summaryLength: number;
  readonly fullLength: number;
}

interface PreparedLorePlan {
  readonly entries: readonly PreparedLoreInjection[];
  readonly modes: LoreInjectionMode[];
}

function headingLine(title: string, mode: LoreInjectionMode): string {
  // Headings stay single-line so each `###` reliably opens exactly one entry;
  // the suffix marks entries whose body was withheld by the budget (#445).
  const encodedTitle = escapePromptData(title.replace(/\s+/g, " ").trim());
  return mode === "full" ? `### ${encodedTitle}` : `### ${encodedTitle} (summary only)`;
}

function fragmentLines(heading: string, body: string): readonly [string, "", string, ""] {
  return [heading, "", body, ""];
}

function prepareLoreInjection(match: LoreMatch): PreparedLoreInjection {
  // Snapshot source access before deriving both representations. Apart from
  // making getter-backed inputs deterministic, this prevents repeated body
  // scans while evaluating later promotions.
  const title = match.entry.title;
  const contentMarkdown = match.entry.contentMarkdown;
  const summaryBody = escapePromptData(
    loreEntrySummary({
      title,
      loreAliasesJson: match.entry.loreAliasesJson,
      status: match.entry.status,
      contentMarkdown,
    }),
  );
  const fullBody = escapePromptData(contentMarkdown?.trim() ?? "");
  const summaryLines = fragmentLines(headingLine(title, "summary"), summaryBody);
  const fullLines = fragmentLines(headingLine(title, "full"), fullBody);
  return {
    entry: match.entry,
    rank: match.rank,
    summaryLines,
    fullLines,
    summaryLength: summaryLines[0].length + summaryLines[2].length,
    fullLength: fullLines[0].length + fullLines[2].length,
  };
}

function summaryFloorLength(entries: readonly PreparedLoreInjection[]): number {
  // Empty separator lines are already represented by the fixed newline count:
  // four per entry, plus three around the section header and boundary markers.
  return (
    LOREBOOK_SECTION_HEADER.length +
    LOREBOOK_BEGIN.length +
    LOREBOOK_END.length +
    entries.reduce((total, entry) => total + entry.summaryLength, 0) +
    entries.length * 4 +
    3
  );
}

function prepareLorePlan(
  matched: readonly LoreMatch[],
  budgetCharacters: number,
): PreparedLorePlan {
  const entries = matched.map(prepareLoreInjection);
  const modes: LoreInjectionMode[] = entries.map(() => "summary");
  let renderedLength = summaryFloorLength(entries);

  // Two stable passes are sufficient for the closed rank set and preserve
  // reading order within each rank without sorting or copying whole plans.
  for (const rank of ["title", "alias"] as const) {
    for (let index = 0; index < entries.length; index += 1) {
      const entry = entries[index];
      if (entry === undefined || entry.rank !== rank) continue;
      const promotedLength = renderedLength + entry.fullLength - entry.summaryLength;
      if (promotedLength <= budgetCharacters) {
        modes[index] = "full";
        renderedLength = promotedLength;
      }
    }
  }
  return { entries, modes };
}

/**
 * Plan the per-entry injection modes for one prompt: start with every entry
 * at its summary line, then walk the promotion order and upgrade an entry to
 * full text whenever the whole rendered section stays within the budget.
 * Summaries are the floor — an entry that never fits stays visible as a
 * summary line even when the budget cannot hold every summary.
 */
export function planLoreInjections(
  matched: readonly LoreMatch[],
  budgetCharacters: number,
): PlannedLoreInjection[] {
  const prepared = prepareLorePlan(matched, budgetCharacters);
  return prepared.entries.map((entry, index) => ({
    entry: entry.entry,
    mode: prepared.modes[index] ?? "summary",
  }));
}

function preparedInjectionLines(prepared: PreparedLorePlan): string[] {
  if (prepared.entries.length === 0) {
    return [];
  }
  const sections: string[] = ["", LOREBOOK_SECTION_HEADER, LOREBOOK_BEGIN];
  for (let index = 0; index < prepared.entries.length; index += 1) {
    const entry = prepared.entries[index];
    if (entry === undefined) continue;
    sections.push(...(prepared.modes[index] === "full" ? entry.fullLines : entry.summaryLines));
  }
  sections.push(LOREBOOK_END);
  return sections;
}

function fullInjectionLines(entries: readonly LoreEntrySource[]): string[] {
  if (entries.length === 0) return [];
  const sections: string[] = ["", LOREBOOK_SECTION_HEADER, LOREBOOK_BEGIN];
  for (const entry of entries) {
    const title = entry.title;
    const contentMarkdown = entry.contentMarkdown;
    sections.push(
      ...fragmentLines(headingLine(title, "full"), escapePromptData(contentMarkdown?.trim() ?? "")),
    );
  }
  sections.push(LOREBOOK_END);
  return sections;
}

/**
 * Full-text rendering of already-matched entries (the pre-budget layout,
 * retained for the no-budget callers): one reference-data block per entry.
 */
export function renderLoreSection(matched: readonly LoreEntrySource[]): string[] {
  return fullInjectionLines(matched);
}

/** Match then plan then render in one step; an empty result renders nothing. */
export function triggeredLoreSections(
  input: {
    entries: readonly LoreEntrySource[];
    /** Character budget of the rendered section; defaults to the #445 value. */
    budgetCharacters?: number | undefined;
  } & LoreMatchCorpora,
): string[] {
  const matched = matchLoreEntriesWithRank(input.entries, {
    resident: input.resident,
    manuscript: input.manuscript,
  });
  return preparedInjectionLines(
    prepareLorePlan(matched, input.budgetCharacters ?? DEFAULT_LOREBOOK_BUDGET_CHARACTERS),
  );
}
