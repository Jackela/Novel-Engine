import { Type } from "@fastify/type-provider-typebox";
import { jobSummaryPayloadSchema } from "../../application/payload_schemas/job.js";
import type { JsonResponseSchema } from "./json_response_schema.js";

/**
 * The synchronous job payload is the TypeBox SSOT from
 * `application/payload_schemas/job.ts` (#433); the usage surface below stays
 * a hand-written response schema (computed aggregate, not a stored resource).
 */

export { jobPayloadSchema as jobResponseSchema } from "../../application/payload_schemas/job.js";

export const jobListQuerySchema = Type.Object(
  {
    limit: Type.Optional(Type.Integer({ default: 50, minimum: 1, maximum: 100 })),
    cursor: Type.Optional(
      Type.String({
        minLength: 1,
        maxLength: 1024,
        pattern: "^[A-Za-z0-9_-]+$",
      }),
    ),
  },
  { additionalProperties: false },
);

export const jobDetailParamsSchema = Type.Object({
  projectId: Type.String({ minLength: 1, maxLength: 64 }),
  jobId: Type.String({ minLength: 1, maxLength: 64 }),
});

export const jobRetryHeadersSchema = Type.Object({
  "idempotency-key": Type.String({
    minLength: 16,
    maxLength: 128,
    pattern: "^[A-Za-z0-9._~-]+$",
  }),
});

/**
 * The proposal-generation key is optional (DR-027): a request without it
 * keeps the pre-existing behavior, while a present key must satisfy the same
 * character contract as the retry header so both routes share one key format.
 */
export const idempotencyKeyHeadersSchema = Type.Object({
  "idempotency-key": Type.Optional(
    Type.String({
      minLength: 16,
      maxLength: 128,
      pattern: "^[A-Za-z0-9._~-]+$",
    }),
  ),
});

/** The jobs audit listing: newest compact summary first. */
export const jobListResponseSchema = Type.Object(
  {
    jobs: Type.Array(jobSummaryPayloadSchema),
    next_cursor: Type.Unsafe<string | null>({ type: "string", nullable: true }),
  },
  { additionalProperties: false },
);

/** The project usage surface (#317): completed-attempt totals plus a
 * per-model breakdown, failed-attempt/estimated counts (DR-028), and
 * the trailing-30-UTC-day buckets (#384, optional for consumers). */
export const usageResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    project_id: { type: "string" },
    request_count: {
      type: "integer",
      minimum: 0,
      description:
        "Completed provider attempts: the rows every token total folds. Failed attempts are counted separately (DR-028).",
    },
    failed_attempt_count: {
      type: "integer",
      minimum: 0,
      description:
        "Provider attempts that failed without reported usage; they carry zero tokens and never enter the token totals (DR-028).",
    },
    estimated_requests: {
      type: "integer",
      minimum: 0,
      description:
        "Completed attempts whose token counts include a word-count estimate because the provider reported no usage (DR-028).",
    },
    prompt_tokens: { type: "integer", minimum: 0 },
    completion_tokens: { type: "integer", minimum: 0 },
    daily: {
      type: "array",
      description:
        "The last 30 UTC days (today included), zero-filled: one bucket per day, oldest first, completed attempts only (#384, DR-028).",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          date: { type: "string", pattern: "^[0-9]{4}-[0-9]{2}-[0-9]{2}$" },
          request_count: { type: "integer", minimum: 0 },
          prompt_tokens: { type: "integer", minimum: 0 },
          completion_tokens: { type: "integer", minimum: 0 },
        },
        required: ["date", "request_count", "prompt_tokens", "completion_tokens"],
      },
    },
    per_model: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: {
          model: { type: "string" },
          requests: {
            type: "integer",
            minimum: 0,
            description: "Completed provider attempts of this model (DR-028).",
          },
          failed_attempts: { type: "integer", minimum: 0 },
          estimated_requests: { type: "integer", minimum: 0 },
          prompt_tokens: { type: "integer", minimum: 0 },
          completion_tokens: { type: "integer", minimum: 0 },
        },
        required: [
          "model",
          "requests",
          "failed_attempts",
          "estimated_requests",
          "prompt_tokens",
          "completion_tokens",
        ],
      },
    },
  },
  required: [
    "project_id",
    "request_count",
    "failed_attempt_count",
    "estimated_requests",
    "prompt_tokens",
    "completion_tokens",
    "per_model",
  ],
} as const;
