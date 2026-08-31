/** The lorebook lore surface (#315, #444): request and response shapes. */

import { Type } from "@fastify/type-provider-typebox";

import { LORE_STATUSES } from "../../domain/kinds.js";

/**
 * The alias response (#440) and the lifecycle-status response (#444) are the
 * TypeBox payload SSOTs from `application/payload_schemas/lore.ts`,
 * re-exported under their HTTP-surface names: the alias verbs answer the
 * normalized alias list, the status write answers the closed enum envelope.
 */
export {
  loreAliasPayloadSchema as loreAliasResponseSchema,
  loreStatusPayloadSchema as loreStatusResponseSchema,
} from "../../application/payload_schemas/lore.js";

export const loreAliasWriteSchema = Type.Object(
  {
    aliases: Type.Array(Type.String({ maxLength: 240 }), { maxItems: 64 }),
  },
  { additionalProperties: false },
);

/** The lifecycle-status write (#444): a closed enum; anything else is 422. */
export const loreStatusWriteSchema = Type.Object(
  {
    lore_status: Type.Unsafe<(typeof LORE_STATUSES)[number]>({
      type: "string",
      enum: [...LORE_STATUSES],
    }),
  },
  { additionalProperties: false },
);
