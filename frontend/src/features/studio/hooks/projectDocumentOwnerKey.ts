/**
 * Canonical owner key for per-(project, document) state families. The NUL
 * separator cannot occur inside either id, so one key names exactly one pair
 * and the composite format stays a single decision.
 */
export function projectDocumentOwnerKey(projectId: string, documentId: string | null): string {
  return `${projectId}\u0000${documentId ?? ""}`;
}
