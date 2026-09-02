import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import {
  EXPORT_CAPACITY_RESOURCES,
  GENERATION_CAPACITY_RESOURCES,
} from "../../domain/exceptions.js";
import {
  exportCapacityEnvelope,
  invalidOperationEnvelope,
  validationErrorEnvelope,
} from "./export_capacity_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";

const generationCapacityEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.GENERATION_CAPACITY_EXCEEDED] },
        message: { type: "string", enum: ["Generation capacity exceeded."] },
        details: {
          type: "object",
          additionalProperties: false,
          properties: {
            resource: { type: "string", enum: [...GENERATION_CAPACITY_RESOURCES] },
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

export const proposalGeneration422ResponseSchema: JsonResponseSchema = {
  description: "Invalid proposal input or permanent generation-capacity refusal.",
  content: {
    "application/json": {
      schema: {
        oneOf: [invalidOperationEnvelope, generationCapacityEnvelope, validationErrorEnvelope],
      },
    },
  },
} as const;

export const jobRetry422ResponseSchema: JsonResponseSchema = {
  description: "Invalid retry input or permanent export/generation capacity outcome.",
  content: {
    "application/json": {
      schema: {
        oneOf: [
          invalidOperationEnvelope,
          exportCapacityEnvelope(EXPORT_CAPACITY_RESOURCES),
          generationCapacityEnvelope,
          validationErrorEnvelope,
        ],
      },
    },
  },
} as const;
