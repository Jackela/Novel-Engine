const timestamp = { type: "string", format: "date-time" } as const;
const evidenceSchema = { type: "object", additionalProperties: true } as const;

/**
 * A review has no client-controlled input. Provider and model provenance are
 * selected inside the server's service graph rather than accepted over HTTP.
 */
export const reviewCreateSchema = {
  type: "object",
  properties: {},
  additionalProperties: false,
} as const;

const reviewIssueResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    id: { type: "string" },
    document_id: { type: "string" },
    severity: { type: "string", enum: ["blocker", "warning", "suggestion"] },
    code: { type: "string" },
    message: { type: "string" },
    suggestion: { type: "string" },
    evidence: evidenceSchema,
  },
  required: ["id", "document_id", "severity", "code", "message", "suggestion", "evidence"],
} as const;

/** Stable snake_case response consumed by the frontend workflow parser. */
export const reviewResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    id: { type: "string" },
    project_id: { type: "string" },
    snapshot_id: { type: "string" },
    provider: { type: "string" },
    model: { type: "string" },
    summary: { type: "string" },
    created_at: timestamp,
    issues: { type: "array", items: reviewIssueResponseSchema },
  },
  required: [
    "id",
    "project_id",
    "snapshot_id",
    "provider",
    "model",
    "summary",
    "created_at",
    "issues",
  ],
} as const;

export const reviewListResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: { reviews: { type: "array", items: reviewResponseSchema } },
  required: ["reviews"],
} as const;
