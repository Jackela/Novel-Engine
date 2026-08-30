import { type Static, Type } from "@fastify/type-provider-typebox";
import { freeFormObject, nullableString } from "./common.js";
import { documentPayloadSchema } from "./document.js";
import { volumePayloadSchema } from "./volume.js";

/**
 * Project payload (#433 SSOT): the list form emitted by `projectPayload`
 * without optional arguments, and the detail form (nested `documents` and
 * `volumes`) emitted when both are supplied. Both share the flat properties
 * exactly as the previous hand-written schemas did; only the detail form
 * marks the nested arrays required.
 */
const projectProperties = {
  id: Type.String(),
  title: Type.String(),
  description: Type.String(),
  settings: freeFormObject,
  import_hash: nullableString,
  created_at: Type.String(),
  updated_at: Type.String(),
} as const;

export const projectPayloadSchema = Type.Object(
  {
    ...projectProperties,
    documents: Type.Optional(Type.Array(documentPayloadSchema)),
    volumes: Type.Optional(Type.Array(volumePayloadSchema)),
  },
  { additionalProperties: false },
);

export type ProjectPayload = Static<typeof projectPayloadSchema>;

export const projectDetailPayloadSchema = Type.Object(
  {
    ...projectProperties,
    documents: Type.Array(documentPayloadSchema),
    volumes: Type.Array(volumePayloadSchema),
  },
  { additionalProperties: false },
);

export type ProjectDetailPayload = Static<typeof projectDetailPayloadSchema>;
