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
