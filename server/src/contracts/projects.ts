/**
 * Project and volume contracts. One schema per wire shape; the same object
 * drives Fastify request validation, response serialization, the OpenAPI
 * document, and the client's runtime check.
 *
 * Naming: wire fields are camelCase end to end. Database columns stay
 * snake_case and are mapped only inside the SQLite adapter.
 */

import { Type, type Static } from "typebox";

export const ProjectId = Type.String({ minLength: 1, maxLength: 64 });
export type ProjectId = Static<typeof ProjectId>;

export const VolumeId = Type.String({ minLength: 1, maxLength: 64 });
export type VolumeId = Static<typeof VolumeId>;

/**
 * Epoch milliseconds, not seconds: the legacy database stores `timestamp_ms`,
 * `Date.now()` yields milliseconds, and the migration copies values verbatim.
 * Naming it for the unit avoids a silent 1000x error at every boundary.
 */
export const EpochMillis = Type.Integer({ minimum: 0 });
export type EpochMillis = Static<typeof EpochMillis>;

/** A project as the library lists it. */
export const ProjectView = Type.Object(
  {
    id: ProjectId,
    title: Type.String({ maxLength: 200 }),
    description: Type.String(),
    volumeCount: Type.Integer({ minimum: 0 }),
    documentCount: Type.Integer({ minimum: 0 }),
    createdAt: EpochMillis,
    updatedAt: EpochMillis,
  },
  { additionalProperties: false },
);
export type ProjectView = Static<typeof ProjectView>;

export const ProjectCreateRequest = Type.Object(
  {
    title: Type.String({ minLength: 1, maxLength: 200 }),
    description: Type.String({ maxLength: 4_000 }),
  },
  { additionalProperties: false },
);
export type ProjectCreateRequest = Static<typeof ProjectCreateRequest>;

/** Partial update: omitted fields stay unchanged; null clears description. */
export const ProjectUpdateRequest = Type.Object(
  {
    title: Type.Optional(Type.String({ minLength: 1, maxLength: 200 })),
    description: Type.Optional(Type.Union([Type.String({ maxLength: 4_000 }), Type.Null()])),
  },
  { additionalProperties: false },
);
export type ProjectUpdateRequest = Static<typeof ProjectUpdateRequest>;

export const VolumeView = Type.Object(
  {
    id: VolumeId,
    projectId: ProjectId,
    title: Type.String({ maxLength: 200 }),
    position: Type.Integer({ minimum: 0 }),
    createdAt: EpochMillis,
  },
  { additionalProperties: false },
);
export type VolumeView = Static<typeof VolumeView>;

export const VolumeCreateRequest = Type.Object(
  {
    title: Type.String({ minLength: 1, maxLength: 200 }),
    position: Type.Optional(Type.Integer({ minimum: 0 })),
  },
  { additionalProperties: false },
);
export type VolumeCreateRequest = Static<typeof VolumeCreateRequest>;

export const VolumeRenameRequest = Type.Object(
  { title: Type.String({ minLength: 1, maxLength: 200 }) },
  { additionalProperties: false },
);
export type VolumeRenameRequest = Static<typeof VolumeRenameRequest>;

/** Keyset pagination, one protocol for every list endpoint. */
export const PageQuery = Type.Object(
  {
    limit: Type.Optional(Type.Integer({ minimum: 1, maximum: 100 })),
    cursor: Type.Optional(Type.String({ maxLength: 512 })),
  },
  { additionalProperties: false },
);
export type PageQuery = Static<typeof PageQuery>;

export const PageInfo = Type.Object(
  {
    nextCursor: Type.Union([Type.String(), Type.Null()]),
    hasMore: Type.Boolean(),
  },
  { additionalProperties: false },
);
export type PageInfo = Static<typeof PageInfo>;

export const ProjectPage = Type.Object(
  {
    items: Type.Array(ProjectView),
    page: PageInfo,
  },
  { additionalProperties: false },
);
export type ProjectPage = Static<typeof ProjectPage>;
