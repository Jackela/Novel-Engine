import type { RevisionPage, RevisionSummary } from "@/app/types/studio";

export interface RevisionCacheEntry {
  readonly revisions: RevisionSummary[];
  readonly nextCursor: string | null;
  readonly initialized: boolean;
  readonly lastAccess: number;
}

export function appendUnique(
  current: readonly RevisionSummary[],
  additions: readonly RevisionSummary[],
): RevisionSummary[] {
  const known = new Set(current.map((revision) => revision.id));
  return [
    ...current,
    ...additions.filter((revision) => {
      if (known.has(revision.id)) return false;
      known.add(revision.id);
      return true;
    }),
  ];
}

export function mergeFreshPage(
  current: RevisionCacheEntry,
  page: RevisionPage,
): Pick<RevisionCacheEntry, "revisions" | "nextCursor"> {
  if (!current.initialized || page.next_cursor === null) {
    return { revisions: page.revisions, nextCursor: page.next_cursor };
  }
  const currentIds = new Set(current.revisions.map((revision) => revision.id));
  const overlaps = page.revisions.some((revision) => currentIds.has(revision.id));
  if (!overlaps) {
    // Appending across an absent overlap would fabricate a contiguous range.
    return { revisions: page.revisions, nextCursor: page.next_cursor };
  }
  return {
    revisions: appendUnique(page.revisions, current.revisions),
    nextCursor: current.nextCursor,
  };
}
