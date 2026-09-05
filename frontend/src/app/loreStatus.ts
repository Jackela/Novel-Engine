import type { LoreStatus } from "@/app/types/studio";

interface LoreStatusOption {
  readonly value: LoreStatus;
  readonly label: string;
}

type CompleteLoreStatusOptions<Options extends readonly LoreStatusOption[]> =
  Exclude<LoreStatus, Options[number]["value"]> extends never ? Options : never;

function defineLoreStatusOptions<const Options extends readonly LoreStatusOption[]>(
  options: CompleteLoreStatusOptions<Options>,
): Options {
  return options;
}

/**
 * Runtime parser values and author-facing labels for the generated LoreStatus
 * union. The generic constraint rejects both unknown and missing statuses at
 * compile time, so API parsing and the selector cannot drift independently.
 */
export const LORE_STATUS_OPTIONS = defineLoreStatusOptions([
  { value: "draft", label: "Draft (not injected)" },
  { value: "stable", label: "Stable (injected)" },
  { value: "deprecated", label: "Deprecated (not injected)" },
] as const);

export const LORE_STATUSES: readonly LoreStatus[] = LORE_STATUS_OPTIONS.map(({ value }) => value);
