/** The lorebook alias surface (#315): request and response shapes. */

import { Type } from "@fastify/type-provider-typebox";

/**
 * The alias response (#440) is the TypeBox payload SSOT from
 * `application/payload_schemas/lore.ts`, re-exported under its HTTP-surface
 * name: both alias verbs answer the normalized alias list directly.
 */
export { loreAliasPayloadSchema as loreAliasResponseSchema } from "../../application/payload_schemas/lore.js";

export const loreAliasWriteSchema = Type.Object(
  {
    aliases: Type.Array(Type.String({ maxLength: 240 }), { maxItems: 64 }),
  },
  { additionalProperties: false },
);
