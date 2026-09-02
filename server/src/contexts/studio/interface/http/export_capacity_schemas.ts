import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import { EXPORT_CAPACITY_RESOURCES, type ExportCapacityResource } from "../../domain/exceptions.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import {
  invalidOperationEnvelope,
  validationErrorEnvelope,
} from "./unprocessable_entity_schemas.js";

export function exportCapacityEnvelope(resources: readonly ExportCapacityResource[]) {
  return {
    type: "object",
    additionalProperties: false,
    properties: {
      error: {
        type: "object",
        additionalProperties: false,
        properties: {
          code: { type: "string", enum: [ERROR_CODES.EXPORT_CAPACITY_EXCEEDED] },
          message: { type: "string", enum: ["Export capacity exceeded."] },
          details: {
            type: "object",
            additionalProperties: false,
            properties: {
              resource: { type: "string", enum: [...resources] },
              limit: { type: "integer", minimum: 0, maximum: Number.MAX_SAFE_INTEGER },
              observed: { type: "integer", minimum: 1, maximum: Number.MAX_SAFE_INTEGER },
            },
            required: ["resource", "limit", "observed"],
          },
        },
        required: ["code", "message", "details"],
      },
    },
    required: ["error"],
  } as const;
}

/** JSON wrapper prevents binary `produces` metadata from leaking onto error responses. */
export const exportJsonErrorResponseSchema: JsonResponseSchema = {
  content: {
    "application/json": {
      schema: { $ref: "ErrorEnvelope" },
    },
  },
} as const;

export const exportCreateOrRetry422ResponseSchema: JsonResponseSchema = {
  description:
    "Invalid export precondition or permanent export-capacity outcome with bounded evidence.",
  content: {
    "application/json": {
      schema: {
        oneOf: [
          invalidOperationEnvelope,
          exportCapacityEnvelope(EXPORT_CAPACITY_RESOURCES),
          validationErrorEnvelope,
        ],
      },
    },
  },
} as const;

export const exportDownload422ResponseSchema: JsonResponseSchema = {
  description: "Permanent artifact download capacity refusal with bounded evidence.",
  content: {
    "application/json": {
      schema: exportCapacityEnvelope(["artifact_bytes"]),
    },
  },
} as const;
