import type { DocumentSummary, Project } from "@/app/types/studio";

export interface WholeBookChapter {
  readonly id: string;
  readonly title: string;
  /**
   * True when the chapter's current revision holds non-empty text the author
   * has not accepted from AI. A whole-book run drafts such a chapter only
   * after an explicit per-run confirmation (#DR-007).
   */
  readonly requiresConfirmation: boolean;
}

/** The reading-order plan, split by whether a run may start without confirmation. */
export interface WholeBookPlan {
  /** Every chapter a whole-book run could touch, in reading order. */
  readonly chapters: readonly WholeBookChapter[];
  /** Empty chapters: the loop may draft and accept them right away. */
  readonly safe: readonly WholeBookChapter[];
  /** Occupied chapters: replaced only after an explicit confirmation. */
  readonly confirmation: readonly WholeBookChapter[];
}

/**
 * #318 candidate rule: a chapter is a whole-book candidate iff its current
 * revision was not produced by an accepted AI proposal. The server's closed
 * revision-source vocabulary is `author | ai-accepted | restore`
 * (`server/src/contexts/studio/domain/kinds.ts`), so seeded, hand-written,
 * imported, and restored chapters are all candidates. Candidates are then
 * split by their current text: only an empty chapter may be drafted without
 * confirmation (#DR-007).
 */
export function needsGeneration(document: DocumentSummary): boolean {
  return document.revision_source !== "ai-accepted";
}

/**
 * Reading order per ADR-0005: volume position first, then in-volume chapter
 * position. Chapters without a resolved volume link fall back to the first
 * volume exactly like the navigator's grouping, even though ADR-0005
 * guarantees every chapter is placed.
 */
export function readingOrderChapters(project: Project): DocumentSummary[] {
  const chapters = project.documents.filter((document) => document.kind === "chapter");
  const volumes = [...project.volumes].sort((left, right) => left.position - right.position);
  const volumeRank = new Map(volumes.map((volume, index) => [volume.id, index]));
  const fallbackRank = volumes.length > 0 ? (volumeRank.get(volumes[0].id) ?? 0) : 0;
  const rankOf = (document: DocumentSummary): number =>
    document.volume_id ? (volumeRank.get(document.volume_id) ?? fallbackRank) : fallbackRank;
  // filter() above already produced a fresh array, so sorting it never
  // mutates the project payload's own list.
  return chapters.sort((left, right) => {
    const leftRank = rankOf(left);
    const rightRank = rankOf(right);
    return leftRank !== rightRank ? leftRank - rightRank : left.position - right.position;
  });
}

/**
 * The reading-order plan behind the whole-book control: the candidate chapters
 * split into the safe set (empty current text — the document summary carries
 * no body, so `word_count === 0` is the emptiness signal) and the confirmation
 * set (existing author/restored/imported text whose revision is not
 * `ai-accepted`). Revisions are immutable, so a replaced chapter stays
 * restorable from document history. Recomputed on every render and at every
 * start, which is what makes resume work: starting again re-derives the plan
 * from the refreshed summaries, so a chapter that was never replaced asks for
 * confirmation again instead of being silently regenerated (#318, #DR-007).
 */
export function wholeBookPlan(project: Project): WholeBookPlan {
  const chapters: WholeBookChapter[] = [];
  const safe: WholeBookChapter[] = [];
  const confirmation: WholeBookChapter[] = [];
  for (const document of readingOrderChapters(project)) {
    if (!needsGeneration(document)) continue;
    const chapter: WholeBookChapter = {
      id: document.id,
      title: document.title,
      requiresConfirmation: document.word_count > 0,
    };
    chapters.push(chapter);
    (chapter.requiresConfirmation ? confirmation : safe).push(chapter);
  }
  return { chapters, safe, confirmation };
}
