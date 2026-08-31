/** The closed set of authoring document kinds (mirrors the Python authority). */
export const DOCUMENT_KINDS = ["chapter", "outline", "character", "world", "note"] as const;

export type DocumentKind = (typeof DOCUMENT_KINDS)[number];

export function isDocumentKind(value: string): value is DocumentKind {
  return (DOCUMENT_KINDS as readonly string[]).includes(value);
}

/**
 * The server-assigned revision source enum. Request schemas never expose a
 * source field; the value is decided by the operation the server performed
 * (save → author, restore → restore, accepted AI proposal → ai-accepted).
 */
export const REVISION_SOURCES = ["author", "ai-accepted", "restore"] as const;

export type RevisionSource = (typeof REVISION_SOURCES)[number];

/**
 * The lore-entry lifecycle status (#444, ADR-0006): a closed enum carried by
 * character/world documents. Only `stable` entries participate in
 * keyword-triggered injection; `draft` keeps half-written entries out of the
 * prompt and `deprecated` retires entries without deleting them. New lore
 * entries start at `draft`; existing entries migrated to `stable` because
 * they are the author's already-approved canon.
 */
export const LORE_STATUSES = ["draft", "stable", "deprecated"] as const;

export type LoreStatus = (typeof LORE_STATUSES)[number];

export function isLoreStatus(value: string): value is LoreStatus {
  return (LORE_STATUSES as readonly string[]).includes(value);
}

/** The lifecycle status every newly created lore entry starts at (#444). */
export const DEFAULT_LORE_STATUS: LoreStatus = "draft";

/** The only lifecycle status that participates in lorebook injection (#444). */
export const INJECTABLE_LORE_STATUS: LoreStatus = "stable";
