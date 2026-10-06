export type HistoryDiffKind = "context" | "added" | "removed";

export interface HistoryDiffLine {
  readonly kind: HistoryDiffKind;
  readonly text: string;
}

/** A diff line paired with a stable React key (duplicate lines included). */
export interface HistoryDiffRow extends HistoryDiffLine {
  readonly key: string;
}

/**
 * Pair each diff line with a stable presentation key: kind plus text plus an
 * occurrence counter, so repeated lines never collide and no array index ever
 * reaches a React key.
 */
export function historyDiffRows(lines: readonly HistoryDiffLine[]): HistoryDiffRow[] {
  const seen = new Map<string, number>();
  return lines.map((line) => {
    const signature = `${line.kind}:${line.text}`;
    const occurrence = seen.get(signature) ?? 0;
    seen.set(signature, occurrence + 1);
    return { ...line, key: `${signature}:${occurrence}` };
  });
}

/** Cell budget for the LCS table; beyond it the middle degrades to a block replace. */
const MAX_LCS_CELLS = 250_000;

/**
 * Deterministic line diff for the DR-011 history preview: `previous` is the
 * previewed revision, `next` the loaded current revision. Common prefix and
 * suffix stay context; the trimmed middle walks a longest-common-subsequence
 * table (removals win ties, so equal inputs always produce one fixed order).
 * Documents whose changed middle exceeds the cell budget fall back to
 * all-removed-then-all-added, which is coarser but still deterministic.
 */
export function diffHistoryLines(previous: string, next: string): HistoryDiffLine[] {
  const before = previous.split("\n");
  const after = next.split("\n");
  let start = 0;
  while (start < before.length && start < after.length && before[start] === after[start]) {
    start += 1;
  }
  let endBefore = before.length;
  let endAfter = after.length;
  while (endBefore > start && endAfter > start && before[endBefore - 1] === after[endAfter - 1]) {
    endBefore -= 1;
    endAfter -= 1;
  }
  const prefix = before.slice(0, start).map((text) => ({ kind: "context" as const, text }));
  const suffix = before.slice(endBefore).map((text) => ({ kind: "context" as const, text }));
  return [
    ...prefix,
    ...diffMiddle(before.slice(start, endBefore), after.slice(start, endAfter)),
    ...suffix,
  ];
}

function diffMiddle(before: readonly string[], after: readonly string[]): HistoryDiffLine[] {
  if (before.length === 0) {
    return after.map((text) => ({ kind: "added" as const, text }));
  }
  if (after.length === 0) {
    return before.map((text) => ({ kind: "removed" as const, text }));
  }
  if (before.length * after.length > MAX_LCS_CELLS) {
    return [
      ...before.map((text) => ({ kind: "removed" as const, text })),
      ...after.map((text) => ({ kind: "added" as const, text })),
    ];
  }
  const width = after.length + 1;
  const table = new Int32Array((before.length + 1) * width);
  for (let i = before.length - 1; i >= 0; i -= 1) {
    for (let j = after.length - 1; j >= 0; j -= 1) {
      const previousLine = before[i] as string;
      table[i * width + j] =
        previousLine === after[j]
          ? (table[(i + 1) * width + (j + 1)] as number) + 1
          : Math.max(table[(i + 1) * width + j] as number, table[i * width + (j + 1)] as number);
    }
  }
  const lines: HistoryDiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < before.length && j < after.length) {
    if (before[i] === after[j]) {
      lines.push({ kind: "context", text: before[i] as string });
      i += 1;
      j += 1;
    } else if ((table[(i + 1) * width + j] as number) >= (table[i * width + (j + 1)] as number)) {
      lines.push({ kind: "removed", text: before[i] as string });
      i += 1;
    } else {
      lines.push({ kind: "added", text: after[j] as string });
      j += 1;
    }
  }
  while (i < before.length) {
    lines.push({ kind: "removed", text: before[i] as string });
    i += 1;
  }
  while (j < after.length) {
    lines.push({ kind: "added", text: after[j] as string });
    j += 1;
  }
  return lines;
}
