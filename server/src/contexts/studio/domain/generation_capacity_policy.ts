/** Fixed inclusive Provider-prompt budget; no caller may override it. */
export const GENERATION_PROMPT_BYTE_LIMIT = 8_388_608;

/**
 * Fixed inclusive per-segment budget of the lorebook wizard's extraction
 * (#614); no request may override it. Checked in Unicode code points before
 * provider construction, separately from the assembled-prompt byte budget.
 */
export const LORE_EXTRACT_SEGMENT_CODE_POINT_LIMIT = 100_000;

/**
 * The generation-capacity resource vocabulary. `prompt_bytes` is the shared
 * assembled-prompt byte authority; `lore_extract_segment` is the lorebook
 * wizard's per-segment Unicode code-point cap. Both fail closed through the
 * same stable 422 envelope, each pinned to its own fixed limit.
 */
export const GENERATION_CAPACITY_RESOURCES = Object.freeze([
  "prompt_bytes",
  "lore_extract_segment",
] as const);
export type GenerationCapacityResource = (typeof GENERATION_CAPACITY_RESOURCES)[number];
