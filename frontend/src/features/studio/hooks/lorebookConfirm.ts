import { api } from "@/app/api";
import { translateActive } from "@/app/i18n/translate";
import type { MergedLoreCandidate } from "./loreCandidateMerge";
import { toErrorMessage } from "./toErrorMessage";

/** The alias write side's fixed limits (#315), mirrored for the wizard's confirm-time pre-check. */
export const LORE_ALIAS_MAX_COUNT = 64;
export const LORE_ALIAS_MAX_LENGTH = 240;

/** Which write-side alias limit a candidate's effective aliases violate, if any. */
export type LoreAliasLimitError = "count" | "length";

/**
 * Pre-check one candidate's effective aliases against the alias write's
 * fixed limits so the author is told before confirming, instead of waiting
 * for the write's 422 after the entry already exists.
 */
export function loreAliasLimitError(aliases: readonly string[]): LoreAliasLimitError | null {
  if (aliases.length > LORE_ALIAS_MAX_COUNT) return "count";
  for (const alias of aliases) {
    if (alias.length > LORE_ALIAS_MAX_LENGTH) return "length";
  }
  return null;
}

/** The three honest per-candidate outcomes of the two-step confirmation. */
export type LoreConfirmOutcome = "created" | "created-with-failed-aliases" | "failed";

export interface LoreConfirmResult {
  readonly key: string;
  readonly kind: MergedLoreCandidate["kind"];
  readonly title: string;
  /** The aliases that were attempted; kept when the alias write fails. */
  readonly aliases: string[];
  readonly outcome: LoreConfirmOutcome;
  readonly error: string | null;
  /** The created entry's identity; null only when creation itself failed. */
  readonly documentId: string | null;
}

/**
 * Confirm one wizard candidate (#614): the existing lorebook document
 * creation call, then the existing Lore alias write path for its aliases —
 * two deliberately non-atomic steps, reported honestly per candidate. A
 * failed alias write never silently drops the aliases; they stay on the
 * result for retry.
 */
export async function confirmLoreCandidate(
  projectId: string,
  candidate: MergedLoreCandidate,
  aliases: string[],
): Promise<LoreConfirmResult> {
  let documentId: string;
  try {
    const created = await api.createDocument(projectId, {
      kind: candidate.kind,
      title: candidate.title,
      content_markdown: candidate.summary,
    });
    documentId = created.id;
  } catch (reason) {
    return {
      key: candidate.key,
      kind: candidate.kind,
      title: candidate.title,
      aliases,
      outcome: "failed",
      error: toErrorMessage(reason, translateActive("lore.error.confirm")),
      documentId: null,
    };
  }
  const aliasWrite = await writeLoreAliases(projectId, documentId, aliases);
  return {
    key: candidate.key,
    kind: candidate.kind,
    title: candidate.title,
    aliases,
    outcome: aliasWrite.ok ? "created" : "created-with-failed-aliases",
    error: aliasWrite.ok ? null : aliasWrite.error,
    documentId,
  };
}

/** One alias write attempt; the caller owns whether it settles or retries. */
export async function writeLoreAliases(
  projectId: string,
  documentId: string,
  aliases: string[],
): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    await api.saveDocumentAliases(projectId, documentId, aliases);
    return { ok: true };
  } catch (reason) {
    return { ok: false, error: toErrorMessage(reason, translateActive("lore.error.aliasWrite")) };
  }
}
