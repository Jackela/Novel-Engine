import type {
  AddJobInput,
  AddUsageEventInput,
  ClaimJobRetryInput,
  CompleteJobWithUsageInput,
  FailedJobErrorRecord,
  JobPageInput,
  JobPageLimit,
  JobRecord,
  JobRetryClaim,
  JobSummaryPage,
  MarkJobOutcomeInput,
  RecordCompletedJobWithUsageInput,
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
  /** Read a previously reserved retry identity without admitting new work. */
  findJobRetry(
    scope: ProjectScope,
    projectId: string,
    sourceJobId: string,
    requestKey: string,
  ): JobRecord | null;
  /** Reserve a retry and its first event atomically, or replay its terminal Job. */
  claimJobRetry(scope: ProjectScope, input: ClaimJobRetryInput): JobRetryClaim;
  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void;
  /**
   * The atomic completed-job-with-usage landing (#392): job row plus usage
   * event, or nothing. Shared by every provider-backed kind that records
   * usage (proposal, lore-extract).
   */
  recordCompletedJobWithUsage(
    scope: ProjectScope,
    input: RecordCompletedJobWithUsageInput,
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
  /** The lightweight jobs audit index, newest summary first with no nested bodies. */
  collectProjectJobSummaries(
    scope: ProjectScope,
    projectId: string,
    input: JobPageInput,
  ): JobSummaryPage;
  /**
   * The diagnostics export's failure scan (#654): this project's most
   * recent failed Jobs (`updated_at DESC`, id tiebreak) with their
   * persisted error messages — a bounded parameterized query, not a
   * paging-window approximation, so "no failures" always means none.
   */
  collectRecentFailedJobErrors(
    scope: ProjectScope,
    projectId: string,
    limit: JobPageLimit,
  ): FailedJobErrorRecord[];
  /** Transition a persisted job and append its matching event atomically. */
  markJobOutcome(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: MarkJobOutcomeInput,
  ): JobRecord;
}
