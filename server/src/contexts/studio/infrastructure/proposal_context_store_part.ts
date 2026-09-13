import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  ProposalContextSource,
  ProposalContextStore,
} from "../application/ports/proposal_context_store.js";
import type { ProjectScope } from "../application/ports/studio_store.js";
import {
  documentsWithCurrent,
  scopedDocument,
  scopedProject,
  type Tx,
  volumesInOrder,
} from "./db/studio_query_helpers.js";

/** Captures every database-owned proposal input inside one short read transaction. */
export class ProposalContextStorePart implements ProposalContextStore {
  constructor(protected readonly db: StudioSqliteDatabase) {}

  readProposalContext(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
  ): ProposalContextSource {
    return this.db.transaction((tx) => {
      const project = scopedProject(tx, scope, projectId);
      const scopedTarget = scopedDocument(tx, scope, project.id, documentId);
      this.afterScopedTargetRead(tx, scopedTarget.id);

      const capturedDocuments = documentsWithCurrent(tx, project.id);
      const target = capturedDocuments.find((document) => document.id === scopedTarget.id);
      if (target === undefined) {
        throw new Error("Scoped proposal target disappeared during its read transaction.");
      }
      return {
        projectId: project.id,
        target,
        documents: capturedDocuments,
        volumes: volumesInOrder(tx, project.id),
      };
    });
  }

  /** Deterministic test checkpoint after the snapshot's first scoped target read. */
  protected afterScopedTargetRead(_tx: Tx, _documentId: string): void {}
}
