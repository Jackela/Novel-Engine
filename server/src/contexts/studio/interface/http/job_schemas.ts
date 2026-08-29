import type { JsonResponseSchema } from "./json_response_schema.js";

const timestamp = { type: "string" } as const;
const metadataObject = { type: "object", additionalProperties: true } as const;

const jobEventSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    id: { type: "string" },
    status: { type: "string" },
    details: metadataObject,
    created_at: timestamp,
  },
  required: ["id", "status", "details", "created_at"],
} as const;

/** The synchronous job payload: request/result JSON plus the event trail. */
export const jobResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    id: { type: "string" },
    project_id: { type: "string" },
    document_id: { type: "string", nullable: true },
    kind: { type: "string" },
    operation: { type: "string" },
    status: { type: "string" },
    provider: { type: "string" },
    model: { type: "string" },
    request: metadataObject,
    result: metadataObject,
    error: { type: "string", nullable: true },
    retry_of_job_id: { type: "string", nullable: true },
    created_at: timestamp,
    updated_at: timestamp,
    events: {
      type: "array",
      items: jobEventSchema,
      description:
        "Chronological trail (oldest first) on a single job payload; the jobs LIST endpoint is the spec-mandated newest-first surface.",
    },
  },
  required: [
    "id",
    "project_id",
    "document_id",
    "kind",
    "operation",
    "status",
    "provider",
    "model",
    "request",
    "result",
    "error",
    "retry_of_job_id",
    "created_at",
    "updated_at",
    "events",
  ],
} as const;

/** The jobs audit listing: newest job first, each event newest first. */
export const jobListResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { jobs: { type: "array", items: jobResponseSchema } },
  required: ["jobs"],
} as const;

/** The project usage surface (#317): totals plus a per-model breakdown and
 * the trailing-30-UTC-day buckets (#384, optional for consumers). */
export const usageResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    project_id: { type: "string" },
    request_count: { type: "integer", minimum: 0 },
    prompt_tokens: { type: "integer", minimum: 0 },
    completion_tokens: { type: "integer", minimum: 0 },
    daily: {
      type: "array",
      description:
        "The last 30 UTC days (today included), zero-filled: one bucket per day, oldest first (#384).",
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
          requests: { type: "integer", minimum: 0 },
          prompt_tokens: { type: "integer", minimum: 0 },
          completion_tokens: { type: "integer", minimum: 0 },
        },
        required: ["model", "requests", "prompt_tokens", "completion_tokens"],
      },
    },
  },
  required: ["project_id", "request_count", "prompt_tokens", "completion_tokens", "per_model"],
} as const;
