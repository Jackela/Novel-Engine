import { type Static, Type } from "@fastify/type-provider-typebox";
import { freeFormObject, nullableString } from "./common.js";

/** One durable job-event trail entry, as serialized into the job payload. */
const jobEventPayloadSchema = Type.Object(
  {
    id: Type.String(),
    status: Type.String(),
    details: freeFormObject,
    created_at: Type.String(),
  },
  { additionalProperties: false },
);

/**
 * Job payload (#433 SSOT): the synchronous job row with its parsed
 * request/result JSON and the chronological event trail (oldest first).
 */
export const jobPayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    document_id: nullableString,
    kind: Type.String(),
    operation: Type.String(),
    status: Type.String(),
    provider: Type.String(),
    model: Type.String(),
    request: freeFormObject,
    result: freeFormObject,
    error: nullableString,
    retry_of_job_id: nullableString,
    created_at: Type.String(),
    updated_at: Type.String(),
    events: Type.Array(jobEventPayloadSchema, {
      description:
        "Chronological trail (oldest first) on a single job payload; the jobs LIST endpoint is the spec-mandated newest-first surface.",
    }),
  },
  { additionalProperties: false },
);

export const JOB_SUMMARY_KINDS = ["proposal", "review", "export", "import"] as const;
export const JOB_SUMMARY_OPERATIONS = [
  "continue",
  "rewrite",
  "generate",
  "review",
  "export",
  "import",
] as const;
export const JOB_SUMMARY_STATUSES = [
  "pending",
  "running",
  "completed",
  "failed",
  "interrupted",
] as const;

/** Compact project-history item; nested request/result/event bodies require Job detail. */
export const jobSummaryPayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    document_id: nullableString,
    kind: Type.Unsafe<(typeof JOB_SUMMARY_KINDS)[number]>({
      type: "string",
      enum: [...JOB_SUMMARY_KINDS],
    }),
    operation: Type.Unsafe<(typeof JOB_SUMMARY_OPERATIONS)[number]>({
      type: "string",
      enum: [...JOB_SUMMARY_OPERATIONS],
    }),
    status: Type.Unsafe<(typeof JOB_SUMMARY_STATUSES)[number]>({
      type: "string",
      enum: [...JOB_SUMMARY_STATUSES],
    }),
    provider: Type.String(),
    model: Type.String(),
    error: nullableString,
    retry_of_job_id: nullableString,
    created_at: Type.String({ format: "date-time" }),
    updated_at: Type.String({ format: "date-time" }),
  },
  { additionalProperties: false },
);

export type JobPayload = Static<typeof jobPayloadSchema>;
export type JobSummaryPayload = Static<typeof jobSummaryPayloadSchema>;
