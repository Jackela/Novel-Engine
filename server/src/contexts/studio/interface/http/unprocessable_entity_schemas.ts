import { ERROR_CODES } from "../../../../shared/interface/http/error_envelope.js";

export const invalidOperationEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.INVALID_OPERATION] },
        message: { type: "string" },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

/**
 * DR-022: the selected provider has no usable credential. The envelope names
 * the missing credential in `message`; no job row and no stream exist.
 */
export const providerNotConfiguredEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.PROVIDER_NOT_CONFIGURED] },
        message: { type: "string" },
      },
      required: ["code", "message"],
    },
  },
  required: ["error"],
} as const;

export const validationErrorEnvelope = {
  type: "object",
  additionalProperties: false,
  properties: {
    error: {
      type: "object",
      additionalProperties: false,
      properties: {
        code: { type: "string", enum: [ERROR_CODES.VALIDATION_ERROR] },
        message: { type: "string", enum: ["Request validation failed."] },
        details: {
          type: "object",
          additionalProperties: false,
          properties: {
            errors: {
              type: "array",
              items: {
                type: "object",
                additionalProperties: false,
                properties: {
                  field: { type: "string" },
                  message: { type: "string" },
                  type: { type: "string" },
                },
                required: ["field", "message", "type"],
              },
            },
          },
          required: ["errors"],
        },
      },
      required: ["code", "message", "details"],
    },
  },
  required: ["error"],
} as const;
