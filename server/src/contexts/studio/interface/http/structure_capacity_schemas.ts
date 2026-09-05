import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";
import { STRUCTURE_CAPACITY_RESOURCES } from "../../domain/structure_capacity.js";
import type { JsonResponseSchema } from "./json_response_schema.js";
import {
  invalidOperationEnvelope,
  validationErrorEnvelope,
} from "./unprocessable_entity_schemas.js";

/**
 * The permanent structure-capacity refusal envelope (#461): fixed message,
 * closed `resource` catalog, inclusive `limit`, and `observed` saturated to
 * at most `limit + 1`. Documentation-only like the generation/export capacity
 * envelopes — runtime serialization stays the permissive error envelope.
 */
const structureCapacityEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.STRUCTURE_CAPACITY_EXCEEDED] },
        message: { type: "string", enum: ["Authoring structure capacity exceeded."] },
        details: {
          type: "object",
          additionalProperties: false,
          properties: {
            resource: { type: "string", enum: [...STRUCTURE_CAPACITY_RESOURCES] },
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

/** The 422 contract shared by every authoring-structure write route. */
export const structureCapacity422ResponseSchema: JsonResponseSchema = {
  description:
    "Invalid input or permanent authoring-structure capacity refusal with bounded evidence.",
  content: {
    "application/json": {
      schema: {
        oneOf: [invalidOperationEnvelope, structureCapacityEnvelope, validationErrorEnvelope],
      },
    },
  },
} as const;
