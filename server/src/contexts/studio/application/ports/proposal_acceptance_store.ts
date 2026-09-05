import type { JobRecord } from "./job_records.js";
import type { ProjectScope } from "./studio_store.js";

/**
 * Atomic persistence boundary for accepting one completed AI proposal. The
 * adapter re-reads the job inside its write transaction so idempotence does
 * not depend on an application-layer check performed before the write lock.
 */
export interface ProposalAcceptanceStore {
  acceptCompletedProposal(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    now: Date,
  ): JobRecord;
}
