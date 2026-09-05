import { type Static, Type } from "@fastify/type-provider-typebox";
import { freeFormObject } from "./common.js";

/**
 * Review payload SSOT (#440): the snapshot-bound editorial assessment emitted
 * by `reviewPayload` for the review LIST surface (#316). Stable snake_case is
 * consumed by the frontend workflow parser; provenance is server-owned, never
 * client input.
 */

/**
 * Read-compatible severity superset: the write path coerces provider findings
 * to "blocker"/"warning" only (`review_rules.ts`); "suggestion" stays in the
 * declared set because stored rows may predate that coercion.
 */
export type ReviewSeverity = "blocker" | "warning" | "suggestion";

export const reviewIssuePayloadSchema = Type.Object(
  {
    id: Type.String(),
    document_id: Type.String(),
    severity: Type.Unsafe<ReviewSeverity>({
      type: "string",
      enum: ["blocker", "warning", "suggestion"],
    }),
    code: Type.String(),
    message: Type.String(),
    suggestion: Type.String(),
    evidence: freeFormObject,
  },
  { additionalProperties: false },
);

export type ReviewIssuePayload = Static<typeof reviewIssuePayloadSchema>;

export const reviewPayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    snapshot_id: Type.String(),
    provider: Type.String(),
    model: Type.String(),
    summary: Type.String(),
    created_at: Type.String({ format: "date-time" }),
    issues: Type.Array(reviewIssuePayloadSchema),
  },
  { additionalProperties: false },
);

export type ReviewPayload = Static<typeof reviewPayloadSchema>;

/**
 * Lightweight review-history item (#459): identity, provenance, the fixed
 * summary text, and the exact issue count. Ordered issues never ride the list.
 */
export const reviewSummaryPayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    snapshot_id: Type.String(),
    provider: Type.String(),
    model: Type.String(),
    summary: Type.String(),
    issue_count: Type.Integer({ minimum: 0 }),
    created_at: Type.String({ format: "date-time" }),
  },
  { additionalProperties: false },
);

export type ReviewSummaryPayload = Static<typeof reviewSummaryPayloadSchema>;
