/**
 * Volume request/response shapes for the fixed two-level hierarchy
 * (ADR-0005). Volume titles follow the project/document title contract.
 * Request schemas are TypeBox; the response schema is the TypeBox payload
 * SSOT from `application/payload_schemas/` (#433).
 */

import { Type } from "@fastify/type-provider-typebox";
import { volumePayloadSchema } from "../../application/payload_schemas/volume.js";

export { volumePayloadSchema as volumeResponseSchema } from "../../application/payload_schemas/volume.js";

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

export const volumeListResponseSchema = Type.Object(
  { volumes: Type.Array(volumePayloadSchema) },
  { additionalProperties: false },
);
