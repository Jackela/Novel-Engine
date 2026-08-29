/** The lorebook alias surface (#315): request and response shapes. */

import { Type } from "@fastify/type-provider-typebox";

export const loreAliasWriteSchema = Type.Object(
  {
    aliases: Type.Array(Type.String({ maxLength: 240 }), { maxItems: 64 }),
  },
  { additionalProperties: false },
);

export const loreAliasResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    aliases: { type: "array", items: { type: "string" } },
  },
  required: ["aliases"],
} as const;
