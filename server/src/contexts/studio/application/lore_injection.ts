import type { LoreEntrySource, LoreMatch, LoreMatchRank } from "./lorebook.js";
import { type LoreMatchCorpora, loreEntrySummary, matchLoreEntriesWithRank } from "./lorebook.js";
import { LOREBOOK_BEGIN, LOREBOOK_END } from "./sanitization.js";

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

/**
 * Deterministic promotion priority (#445): title hits expand before alias
 * hits; equal ranks expand in the match list's reading order. The explicit
 * index tiebreak pins stability regardless of engine sort behavior.
 */
function comparePromotionPriority(
  left: { readonly match: LoreMatch; readonly index: number },
  right: { readonly match: LoreMatch; readonly index: number },
): number {
  const rankOrder = (rank: LoreMatchRank) => (rank === "title" ? 0 : 1);
  return rankOrder(left.match.rank) - rankOrder(right.match.rank) || left.index - right.index;
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
  const plan: PlannedLoreInjection[] = matched.map((match) => ({
    entry: match.entry,
    mode: "summary",
  }));
  const promotionOrder = matched
    .map((match, index) => ({ match, index }))
    .sort(comparePromotionPriority);
  for (const { index } of promotionOrder) {
    const candidate: PlannedLoreInjection[] = plan.map((planned, position) =>
      position === index ? { ...planned, mode: "full" } : planned,
    );
    const upgraded = candidate[index];
    if (upgraded !== undefined && renderedSectionLength(candidate) <= budgetCharacters) {
      plan[index] = upgraded;
    }
  }
  return plan;
}

function headingLine(entry: LoreEntrySource, mode: LoreInjectionMode): string {
  // Headings stay single-line so each `###` reliably opens exactly one entry;
  // the suffix marks entries whose body was withheld by the budget (#445).
  const title = entry.title.replace(/\s+/g, " ").trim();
  return mode === "full" ? `### ${title}` : `### ${title} (summary only)`;
}

function bodyLine(entry: LoreEntrySource, mode: LoreInjectionMode): string {
  return mode === "full" ? (entry.contentMarkdown?.trim() ?? "") : loreEntrySummary(entry);
}

function injectionLines(planned: readonly PlannedLoreInjection[]): string[] {
  if (planned.length === 0) {
    return [];
  }
  const sections: string[] = ["", LOREBOOK_SECTION_HEADER, LOREBOOK_BEGIN];
  for (const injection of planned) {
    sections.push(
      headingLine(injection.entry, injection.mode),
      "",
      bodyLine(injection.entry, injection.mode),
      "",
    );
  }
  sections.push(LOREBOOK_END);
  return sections;
}

function renderedSectionLength(planned: readonly PlannedLoreInjection[]): number {
  return injectionLines(planned).join("\n").length;
}

/**
 * Full-text rendering of already-matched entries (the pre-budget layout,
 * retained for the no-budget callers): one trusted-context block per entry.
 */
export function renderLoreSection(matched: readonly LoreEntrySource[]): string[] {
  return injectionLines(matched.map((entry) => ({ entry, mode: "full" })));
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
  return injectionLines(
    planLoreInjections(matched, input.budgetCharacters ?? DEFAULT_LOREBOOK_BUDGET_CHARACTERS),
  );
}
