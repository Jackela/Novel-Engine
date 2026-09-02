import type { DocumentWithCurrent, ProjectScope, RevisionRecord } from "./studio_store.js";
import type { VolumeRecord } from "./volume_store.js";

/** Immutable revision paired to one document at proposal-context capture. */
export type ProposalContextRevision = Readonly<RevisionRecord>;

/** Immutable document row paired to the revision current in the same snapshot. */
export type ProposalContextDocument = Readonly<
  Omit<DocumentWithCurrent, "currentRevision"> & {
    currentRevision: ProposalContextRevision | null;
  }
>;

/** Immutable volume row in canonical project reading order. */
export type ProposalContextVolume = Readonly<VolumeRecord>;

/** Every database-owned input needed to assemble one proposal task coherently. */
export interface ProposalContextSource {
  readonly projectId: string;
  readonly target: ProposalContextDocument;
  readonly documents: readonly ProposalContextDocument[];
  readonly volumes: readonly ProposalContextVolume[];
}

/** One bounded read snapshot for proposal-context inputs. */
export interface ProposalContextStore {
  readProposalContext(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
  ): ProposalContextSource;
}
