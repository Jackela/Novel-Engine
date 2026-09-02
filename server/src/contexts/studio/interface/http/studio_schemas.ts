import { Type } from "@fastify/type-provider-typebox";
import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import {
  documentSummaryPayloadSchema,
  matchResultPayloadSchema,
} from "../../application/payload_schemas/document.js";
import { projectPayloadSchema } from "../../application/payload_schemas/project.js";
import { revisionSummaryPayloadSchema } from "../../application/payload_schemas/revision.js";
import type { JsonResponseSchema } from "./json_response_schema.js";

/**
 * Core resource response schemas are the TypeBox payload SSOT declared in
 * `application/payload_schemas/` (#433): the objects below are the same
 * schemas the payload builders type their output with, re-exported under
 * their HTTP-surface names. List envelopes wrap those items; conflict and
 * error envelopes stay hand-written JSON Schema.
 */

export {
  documentPayloadSchema as documentResponseSchema,
  matchResultPayloadSchema as matchResultSchema,
} from "../../application/payload_schemas/document.js";
export {
  projectPayloadSchema as projectResponseSchema,
  projectShellPayloadSchema as projectShellResponseSchema,
} from "../../application/payload_schemas/project.js";
export { revisionPayloadSchema as revisionResponseSchema } from "../../application/payload_schemas/revision.js";

export const documentListResponseSchema = Type.Object(
  { documents: Type.Array(documentSummaryPayloadSchema) },
  { additionalProperties: false },
);

export const revisionListResponseSchema = Type.Object(
  {
    revisions: Type.Array(revisionSummaryPayloadSchema),
    next_cursor: Type.Unsafe<string | null>({ type: "string", nullable: true }),
  },
  { additionalProperties: false },
);

export const projectListResponseSchema = Type.Object(
  { projects: Type.Array(projectPayloadSchema) },
  { additionalProperties: false },
);

export const matchListResponseSchema = Type.Object(
  { results: Type.Array(matchResultPayloadSchema) },
  { additionalProperties: false },
);

/** The 409 conflict envelope: details.current_revision_id identifies the winner. */
export const revisionConflictSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.REVISION_CONFLICT] },
        message: { type: "string" },
        details: {
          type: "object",
          additionalProperties: false,
          properties: { current_revision_id: { type: "string", nullable: true } },
          required: ["current_revision_id"],
        },
      },
      required: ["code", "message", "details"],
    },
  },
  required: ["error"],
} as const;

export const documentConflictSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.DOCUMENT_CONFLICT] },
        message: { type: "string" },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

/** The 409 envelope when an identical pipeline operation is already running (#305). */
export const operationInFlightSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.OPERATION_IN_FLIGHT] },
        message: { type: "string" },
        details: {
          type: "object",
          additionalProperties: false,
          properties: {
            project_id: { type: "string" },
            document_id: { type: "string", nullable: true },
            operation: { type: "string" },
          },
          required: ["project_id", "document_id", "operation"],
        },
      },
      required: ["code", "message", "details"],
    },
  },
  required: ["error"],
} as const;

/** The keyed retry conflict documents its fixed replay polling hint. */
export const keyedRetryInFlightResponseSchema: JsonResponseSchema = {
  description: "The retry attempt with this idempotency key is still running.",
  headers: {
    "Retry-After": {
      description: "Wait one second before replaying this same retry attempt.",
      type: "integer",
      const: 1,
    },
  },
  content: {
    "application/json": { schema: operationInFlightSchema },
  },
} as const;

const operationCapacityExceededEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.OPERATION_CAPACITY_EXCEEDED] },
        message: {
          type: "string",
          enum: ["Studio operation capacity is exhausted."],
        },
        details: {
          type: "object",
          additionalProperties: false,
          properties: {
            scope: { type: "string", enum: ["project", "application"] },
            limit: { type: "integer", minimum: 1 },
            in_flight: { type: "integer", minimum: 0 },
            project_id: { type: "string" },
            retry_after_seconds: { type: "integer", minimum: 1 },
          },
          required: ["scope", "limit", "in_flight", "project_id", "retry_after_seconds"],
        },
      },
      required: ["code", "message", "details"],
    },
  },
  required: ["error"],
} as const;

const persistenceUnavailableEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.SERVICE_UNAVAILABLE] },
        message: { type: "string" },
        details: { type: "object", additionalProperties: true },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

/** Capacity-aware 503 contract; Retry-After is absent for persistence outages. */
export const operationCapacityResponseSchema: JsonResponseSchema = {
  description: "Workflow capacity exhaustion or unavailable persistence.",
  headers: {
    "Retry-After": {
      description: "Optional integer-seconds hint emitted only for workflow capacity exhaustion.",
      type: "integer",
      minimum: 1,
    },
  },
  content: {
    "application/json": {
      schema: {
        oneOf: [operationCapacityExceededEnvelope, persistenceUnavailableEnvelope],
      },
    },
  },
} as const;

/** The fixed 409 envelope when an immutable snapshot references the document. */
export const snapshotConflictSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.SNAPSHOT_CONFLICT] },
        message: {
          type: "string",
          enum: ["Document is referenced by an immutable snapshot."],
        },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;
