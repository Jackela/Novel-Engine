/**
 * Volume request/response shapes for the fixed two-level hierarchy
 * (ADR-0005). Volume titles follow the project/document title contract.
 * Request schemas are TypeBox; response schemas stay plain JSON Schema.
 */

import { Type } from "@fastify/type-provider-typebox";
import type { JsonResponseSchema } from "./json_response_schema.js";

const timestamp = { type: "string" } as const;

const volumeTitle = Type.String({ minLength: 1, maxLength: 240 });

export const volumeCreateSchema = Type.Object(
  { title: volumeTitle },
  {
    additionalProperties: false,
  },
);

export const volumeRetitleSchema = Type.Object(
  { title: volumeTitle },
  {
    additionalProperties: false,
  },
);

export const volumeReorderSchema = Type.Object(
  { volume_ids: Type.Array(Type.String(), { minItems: 1 }) },
  { additionalProperties: false },
);

/** Moving a chapter between volumes names the target volume only. */
export const documentPlaceSchema = Type.Object(
  { volume_id: Type.String({ minLength: 1 }) },
  { additionalProperties: false },
);

export const volumeResponseSchema: JsonResponseSchema = {
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

export const volumeListResponseSchema: JsonResponseSchema = {
  type: "object",
  additionalProperties: true,
  properties: { volumes: { type: "array", items: volumeResponseSchema } },
  required: ["volumes"],
} as const;
