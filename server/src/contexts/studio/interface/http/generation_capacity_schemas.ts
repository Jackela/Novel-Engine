import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import { EXPORT_CAPACITY_RESOURCES } from "../../domain/exceptions.js";
import {
  GENERATION_PROMPT_BYTE_LIMIT,
  LORE_EXTRACT_SEGMENT_CODE_POINT_LIMIT,
} from "../../domain/generation_capacity_policy.js";
import { exportCapacityEnvelope } from "./export_capacity_schemas.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import {
  invalidOperationEnvelope,
  validationErrorEnvelope,
} from "./unprocessable_entity_schemas.js";

/**
 * The fixed wire message of the generation-capacity refusal: the schema enum
 * and the error mapping pin this exact literal, while the domain exception's
 * own message is enriched for humans and logs.
 */
export const GENERATION_CAPACITY_MESSAGE = "Generation capacity exceeded.";

/**
 * One complete (resource, limit, observed) refusal combination; the envelope
 * admits exactly these pairs, so a resource can never appear with another
 * resource's limit. `observed` is bounded to the limit plus one by the
 * domain exception's constructor.
 */
function capacityRefusal(resource: string, limit: number) {
  return {
    type: "object" as const,
    additionalProperties: false,
    properties: {
      resource: { type: "string", enum: [resource] },
      limit: { type: "integer", enum: [limit] },
      observed: { type: "integer", enum: [limit + 1] },
    },
    required: ["resource", "limit", "observed"],
  };
}

const generationCapacityDetailsSchema = {
  oneOf: [
    capacityRefusal("prompt_bytes", GENERATION_PROMPT_BYTE_LIMIT),
    capacityRefusal("lore_extract_segment", LORE_EXTRACT_SEGMENT_CODE_POINT_LIMIT),
  ],
};

const generationCapacityEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.GENERATION_CAPACITY_EXCEEDED] },
        message: { type: "string", enum: [GENERATION_CAPACITY_MESSAGE] },
        details: generationCapacityDetailsSchema,
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
