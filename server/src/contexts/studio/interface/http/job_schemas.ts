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
export const jobResponseSchema = {
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
export const jobListResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { jobs: { type: "array", items: jobResponseSchema } },
  required: ["jobs"],
} as const;
