import type { DocumentWithCurrent, ProjectScope } from "./studio_store.js";

/** The association write (#313): a beat title or an explicit null to clear. */
export interface SetBeatReferenceInput {
  beatRef: string | null;
  now: Date;
}

/**
 * Beat-port of the authoring core (#313), kept in its own module so the
 * authoring StudioStore stays within its file-size budget. Method names avoid
 * stems shared with frontend client methods (create/update/delete/move).
 */
export interface StudioBeatStore {
  /**
   * Set or clear a chapter's outline-beat association. The write is
   * document-level state: no revision is minted and existing revisions stay
   * untouched. Only chapters may carry the reference.
   */
  setBeatReference(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetBeatReferenceInput,
  ): DocumentWithCurrent;
}
