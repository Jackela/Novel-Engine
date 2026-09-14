import type { LoreExtractCandidate } from "@/app/types/lore";

/** One completed segment's candidate set, in the session's submission order. */
export interface LoreCandidateSegmentResult {
  readonly segmentId: string;
  readonly candidates: readonly LoreExtractCandidate[];
}

/** A merged suggestion; a session view, never persisted content. */
export interface MergedLoreCandidate {
  /** The deterministic `(kind, title)` identity of the collapsed suggestion. */
  readonly key: string;
  readonly kind: LoreExtractCandidate["kind"];
  readonly title: string;
  /** The union of suggested aliases, first-seen order, exact-match deduped. */
  readonly aliases: string[];
  /** The first occurrence's summary body. */
  readonly summary: string;
  /** How many completed segments proposed this `(kind, title)` pair. */
  readonly segmentCount: number;
}

/**
 * The wizard session's cross-segment merge (#614): candidates with the same
 * kind and title collapse to one suggestion carrying the union of suggested
 * aliases, ordered by kind then title (code-unit comparison — locale-free so
 * re-running the merge over the same completed segments yields the same
 * list). The first-segment occurrence wins the summary; the server stays
 * single-segment and stateless about wizard sessions.
 */
export function mergeLoreCandidates(
  segments: readonly LoreCandidateSegmentResult[],
): MergedLoreCandidate[] {
  const byKey = new Map<string, MergedLoreCandidate>();
  for (const segment of segments) {
    for (const candidate of segment.candidates) {
      const key = candidateKey(candidate.kind, candidate.title);
      const existing = byKey.get(key);
      if (existing === undefined) {
        byKey.set(key, {
          key,
          kind: candidate.kind,
          title: candidate.title,
          aliases: [...candidate.aliases],
          summary: candidate.summary,
          segmentCount: 1,
        });
        continue;
      }
      byKey.set(key, {
        ...existing,
        aliases: unionAliases(existing.aliases, candidate.aliases),
        segmentCount: existing.segmentCount + 1,
      });
    }
  }
  return [...byKey.values()].sort(byKindThenTitle);
}

/** The deterministic identity of one collapsed suggestion. */
export function candidateKey(kind: LoreExtractCandidate["kind"], title: string): string {
  return `${kind}\n${title}`;
}

/** Union with exact-match dedup; a Set keeps the lookup linear-time while the array preserves first-seen order. */
function unionAliases(current: readonly string[], added: readonly string[]): string[] {
  const seen = new Set(current);
  const merged = [...current];
  for (const alias of added) {
    if (seen.has(alias)) continue;
    seen.add(alias);
    merged.push(alias);
  }
  return merged;
}

function byKindThenTitle(a: MergedLoreCandidate, b: MergedLoreCandidate): number {
  if (a.kind !== b.kind) return a.kind < b.kind ? -1 : 1;
  if (a.title === b.title) return 0;
  return a.title < b.title ? -1 : 1;
}
