import type {
  AddJobInput,
  AddUsageEventInput,
  CompleteJobWithUsageInput,
  JobPage,
  JobPageInput,
  JobRecord,
  MarkJobOutcomeInput,
  RecordCompletedProposalJobInput,
} from "./job_records.js";
import type { ProjectUsageAggregate } from "./project_usage.js";
import type { ProjectScope } from "./studio_store.js";

/**
 * The workflow-job half of the studio persistence port (the synchronous jobs
 * model, #268/#272). The combined landing/transition methods (#392) keep the
 * job row and its usage-ledger row in one transaction so a failure between
 * the two writes can never strand a completed job without its usage event.
 */
export interface StudioJobLedgerStore {
  addJob(scope: ProjectScope, input: AddJobInput): JobRecord;
  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void;
  /** The atomic completed-proposal landing: job row plus usage event, or nothing. */
  recordCompletedProposalJob(
    scope: ProjectScope,
    input: RecordCompletedProposalJobInput,
  ): JobRecord;
  /** The atomic retry completion: outcome transition plus usage event, or nothing. */
  markJobOutcomeWithUsage(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: CompleteJobWithUsageInput,
  ): JobRecord;
  aggregateProjectUsage(scope: ProjectScope, projectId: string, now: Date): ProjectUsageAggregate;
  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord;
  /**
   * The jobs audit trail, newest job first and each job's events newest
   * first — the OpenSpec listing contract for the synchronous jobs model.
   */
  collectProjectJobs(scope: ProjectScope, projectId: string, input: JobPageInput): JobPage;
  /** Transition a persisted job and append its matching event atomically. */
  markJobOutcome(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: MarkJobOutcomeInput,
  ): JobRecord;
}
