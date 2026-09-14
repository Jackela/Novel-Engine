import type { MessageKey } from "@/app/i18n/dictionaries/en";
import type { LoreStatus } from "@/app/types/studio";

interface LoreStatusOption {
  readonly value: LoreStatus;
  /**
   * Language-independent fallback label (also the canonical EN text) for
   * non-React consumers; UI surfaces resolve `messageKey` through the
   * dictionaries instead.
   */
  readonly label: string;
  /** Dictionary key for the author-facing selector label. */
  readonly messageKey: MessageKey;
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
  {
    value: "draft",
    label: "Draft (not injected)",
    messageKey: "lore.option.draft",
  },
  {
    value: "stable",
    label: "Stable (injected)",
    messageKey: "lore.option.stable",
  },
  {
    value: "deprecated",
    label: "Deprecated (not injected)",
    messageKey: "lore.option.deprecated",
  },
] as const);

export const LORE_STATUSES: readonly LoreStatus[] = LORE_STATUS_OPTIONS.map(({ value }) => value);
