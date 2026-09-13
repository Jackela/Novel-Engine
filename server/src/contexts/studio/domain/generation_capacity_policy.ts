/** Fixed inclusive Provider-prompt budget; no caller may override it. */
export const GENERATION_PROMPT_BYTE_LIMIT = 8_388_608;

export const GENERATION_CAPACITY_RESOURCES = Object.freeze(["prompt_bytes"] as const);
export type GenerationCapacityResource = (typeof GENERATION_CAPACITY_RESOURCES)[number];
