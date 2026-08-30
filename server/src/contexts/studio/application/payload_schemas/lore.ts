import { type Static, Type } from "@fastify/type-provider-typebox";

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
