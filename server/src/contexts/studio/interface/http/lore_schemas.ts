/** The lorebook alias surface (#315): request and response shapes. */

export const loreAliasWriteSchema = {
  type: "object",
  properties: {
    aliases: {
      type: "array",
      maxItems: 64,
      items: { type: "string", maxLength: 240 },
    },
  },
  required: ["aliases"],
  additionalProperties: false,
} as const;

export const loreAliasResponseSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    aliases: { type: "array", items: { type: "string" } },
  },
  required: ["aliases"],
} as const;
