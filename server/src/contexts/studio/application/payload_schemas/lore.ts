import { type Static, Type } from "@fastify/type-provider-typebox";

import { LORE_STATUSES, type LoreStatus } from "../../domain/kinds.js";

/**
 * Lore-alias payload SSOT (#440): the extra prompt keys of a character or
 * world document as served by the alias surface (#315). The list is always
 * write-normalized (trimmed, deduped, capped), so the response shape is a
 * plain string array with no nullable members.
 */
export const loreAliasPayloadSchema = Type.Object(
  {
    aliases: Type.Array(Type.String()),
  },
  { additionalProperties: false },
);

export type LoreAliasPayload = Static<typeof loreAliasPayloadSchema>;

/**
 * Lore lifecycle-status payload SSOT (#444): the closed lifecycle enum of a
 * character or world document as answered by the lore-status write surface.
 * The closed set is declared from `domain/kinds.ts`, mirroring the document
 * payload's `lore_status` member.
 */
export const loreStatusPayloadSchema = Type.Object(
  {
    lore_status: Type.Unsafe<LoreStatus>({ type: "string", enum: [...LORE_STATUSES] }),
  },
  { additionalProperties: false },
);

export type LoreStatusPayload = Static<typeof loreStatusPayloadSchema>;
