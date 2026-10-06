import { isSafeUsageToken } from "../../../contexts/ai/application/ports/text_generation.js";
import { revisionWordCount } from "../domain/revision_word_count.js";
import type { AttemptUsageInput, UsageTokenSource } from "./ports/job_records.js";

/**
 * DR-028 token provenance: every usage row states how its counts were obtained
 * (`provider`, `estimated`, `unreported`) so a word-count fallback is never
 * mistaken for a provider report and a failed attempt is never invisible.
 */

/** The job kinds whose provider attempts carry usage-ledger rows. */
export function recordsProviderUsage(kind: string): boolean {
  return kind === "proposal" || kind === "lore-extract";
}

/**
 * Provider-reported tokens when they are safe integers, otherwise the exact
 * word count (which approximates one token per Han character for CJK text)
 * labelled as an estimate.
 */
export function resolvedTokenUsage(
  reported: number | null,
  text: string,
): { readonly tokens: number; readonly source: UsageTokenSource } {
  return isSafeUsageToken(reported)
    ? { tokens: reported, source: "provider" }
    : { tokens: revisionWordCount(text), source: "estimated" };
}

/** One estimated side makes the whole row an estimate; never silently `provider`. */
export function rowTokenSource(
  prompt: UsageTokenSource,
  completion: UsageTokenSource,
): UsageTokenSource {
  return prompt === "provider" && completion === "provider" ? "provider" : "estimated";
}

/**
 * The usage row of a provider attempt that failed without provider-reported
 * usage: zero tokens, `unreported`, `failed`. The zero counts state honestly
 * that the attempt consumed tokens the ledger cannot quantify — the row exists
 * so retries and failures stay visible instead of vanishing.
 */
export function unreportedAttemptUsage(input: {
  readonly provider: string;
  readonly requestEvidenceJson: string;
  readonly model?: string | undefined;
}): AttemptUsageInput {
  return {
    provider: input.provider,
    model: input.model ?? "",
    promptTokens: 0,
    completionTokens: 0,
    outcome: "failed",
    tokenSource: "unreported",
    requestEvidenceJson: input.requestEvidenceJson,
  };
}
