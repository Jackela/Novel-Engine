/**
 * Volume request/response shapes for the fixed two-level hierarchy
 * (ADR-0005). Volume titles follow the project/document title contract.
 */

const timestamp = { type: "string" } as const;

export const volumeCreateSchema = {
  type: "object",
  properties: {
    title: { type: "string", minLength: 1, maxLength: 240 },
  },
  required: ["title"],
  additionalProperties: false,
} as const;

export const volumeRetitleSchema = volumeCreateSchema;

export const volumeReorderSchema = {
  type: "object",
  properties: {
    volume_ids: { type: "array", items: { type: "string" }, minItems: 1 },
  },
  required: ["volume_ids"],
  additionalProperties: false,
} as const;

/** Moving a chapter between volumes names the target volume only. */
export const documentPlaceSchema = {
  type: "object",
  properties: {
    volume_id: { type: "string", minLength: 1 },
  },
  required: ["volume_id"],
  additionalProperties: false,
} as const;

export const volumeResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: {
    id: { type: "string" },
    project_id: { type: "string" },
    title: { type: "string" },
    position: { type: "integer" },
    created_at: timestamp,
    updated_at: timestamp,
  },
  required: ["id", "project_id", "title", "position", "created_at", "updated_at"],
} as const;

export const volumeListResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { volumes: { type: "array", items: volumeResponseSchema } },
  required: ["volumes"],
} as const;
