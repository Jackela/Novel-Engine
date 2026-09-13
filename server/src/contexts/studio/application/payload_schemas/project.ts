import { type Static, Type } from "@fastify/type-provider-typebox";
import { freeFormObject, nullableString } from "./common.js";
import { documentSummaryPayloadSchema } from "./document.js";
import { volumePayloadSchema } from "./volume.js";

/**
 * Project payload SSOT: the catalog row contains only project scalars, while
 * the shell adds required structural document summaries and volumes.
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

export const projectPayloadSchema = Type.Object(projectProperties, { additionalProperties: false });

export type ProjectPayload = Static<typeof projectPayloadSchema>;

/**
 * Lightweight catalog row (#458): the list read carries only the scalars the
 * library renders; settings/import metadata stay on the shell/detail payload.
 */
export const projectCatalogSummaryPayloadSchema = Type.Object(
  {
    id: Type.String(),
    title: Type.String(),
    description: Type.String(),
    created_at: Type.String({ format: "date-time" }),
    updated_at: Type.String({ format: "date-time" }),
  },
  { additionalProperties: false },
);

export type ProjectCatalogSummaryPayload = Static<typeof projectCatalogSummaryPayloadSchema>;

export const projectShellPayloadSchema = Type.Object(
  {
    ...projectProperties,
    documents: Type.Array(documentSummaryPayloadSchema),
    volumes: Type.Array(volumePayloadSchema),
  },
  { additionalProperties: false },
);

export type ProjectShellPayload = Static<typeof projectShellPayloadSchema>;
