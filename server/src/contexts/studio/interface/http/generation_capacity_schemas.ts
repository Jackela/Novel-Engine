import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import { EXPORT_CAPACITY_RESOURCES } from "../../domain/exceptions.js";
import {
  GENERATION_CAPACITY_RESOURCES,
  GENERATION_PROMPT_BYTE_LIMIT,
} from "../../domain/generation_capacity_policy.js";
import { exportCapacityEnvelope } from "./export_capacity_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import {
  invalidOperationEnvelope,
  validationErrorEnvelope,
} from "./unprocessable_entity_schemas.js";

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
            limit: { type: "integer", enum: [GENERATION_PROMPT_BYTE_LIMIT] },
            observed: { type: "integer", enum: [GENERATION_PROMPT_BYTE_LIMIT + 1] },
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
