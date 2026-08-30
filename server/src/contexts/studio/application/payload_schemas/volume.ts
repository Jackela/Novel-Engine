import { type Static, Type } from "@fastify/type-provider-typebox";

/**
 * Volume payload (#433 SSOT): the ordered list-level shape emitted by
 * `volumePayload` for every HTTP surface (ADR-0005).
 */
export const volumePayloadSchema = Type.Object(
  {
    id: Type.String(),
    project_id: Type.String(),
    title: Type.String(),
    position: Type.Integer(),
    created_at: Type.String(),
    updated_at: Type.String(),
  },
  { additionalProperties: false },
);

export type VolumePayload = Static<typeof volumePayloadSchema>;
