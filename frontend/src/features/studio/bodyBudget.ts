/**
 * DR-048: the chapter-body budget the editor measures a draft against. The
 * hard limit is the server's request-body limit
 * (`server/src/apps/api/http_server_policy.ts`: `bodyLimit: 1_048_576`); it is
 * a documented soft limit for authors — the editor warns before a save can be
 * refused, and never raises the limit itself.
 */
export const BODY_BUDGET_LIMIT_BYTES = 1_048_576;

/** The share of the budget at which the indicator starts warning. */
const NEAR_LIMIT_RATIO = 0.9;

/** The documented budget level of one draft body. */
export type BodyBudgetLevel = "ok" | "near" | "over";

/** Exact UTF-8 size of the draft; the save body is JSON, so the body budget bounds it. */
export function utf8ByteLength(value: string): number {
  return new TextEncoder().encode(value).length;
}

/** `over` when a save can be refused; `near` when the author should plan to split. */
export function bodyBudgetLevel(bytes: number): BodyBudgetLevel {
  if (bytes > BODY_BUDGET_LIMIT_BYTES) return "over";
  return bytes >= Math.ceil(BODY_BUDGET_LIMIT_BYTES * NEAR_LIMIT_RATIO) ? "near" : "ok";
}

const HAN_CHARACTER = /\p{Script=Han}/gu;
const WORD_RUN = /[\p{L}\p{N}_'-]+/gu;

/**
 * The draft's word count, mirroring the server's unified count
 * (`server/src/contexts/studio/domain/revision_word_count.ts`): one Han
 * character counts individually, everything else counts as maximal
 * letter/digit/underscore/apostrophe/hyphen runs. Total, never throws.
 */
export function draftWordCount(value: string): number {
  const hanCount = value.match(HAN_CHARACTER)?.length ?? 0;
  const runCount = value.replace(HAN_CHARACTER, " ").match(WORD_RUN)?.length ?? 0;
  return hanCount + runCount;
}

/** Human-scale size label ("512 KB", "1.0 MB") for the budget indicator. */
export function formatBudgetBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const kilobytes = bytes / 1024;
  return kilobytes < 1024 ? `${Math.round(kilobytes)} KB` : `${(kilobytes / 1024).toFixed(1)} MB`;
}
