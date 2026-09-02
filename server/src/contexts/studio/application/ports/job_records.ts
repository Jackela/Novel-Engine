/** Job-row shapes for the synchronous jobs model (#268/#272). */

/** One durable job-event trail entry. */
export interface JobEventRecord {
  id: string;
  jobId: string;
  status: string;
  detailsJson: string;
  createdAt: Date;
}

/** A workflow job with its event trail (the synchronous jobs model's row). */
export interface JobRecord {
  id: string;
  projectId: string;
  documentId: string | null;
  kind: string;
  operation: string;
  status: string;
  provider: string;
  model: string;
  requestJson: string;
  resultJson: string;
  error: string | null;
  retryOfJobId: string | null;
  createdAt: Date;
  updatedAt: Date;
  events: JobEventRecord[];
}

/** Lightweight project-history item; complete audit bodies live on JobRecord. */
export interface JobSummaryRecord {
  id: string;
  projectId: string;
  documentId: string | null;
  kind: string;
  operation: string;
  status: string;
  provider: string;
  model: string;
  error: string | null;
  retryOfJobId: string | null;
  createdAt: Date;
  updatedAt: Date;
}

/** The validated row budget of one bounded project-job history page. */
export type JobPageLimit = number & { readonly __jobPageLimit: unique symbol };

/** Inclusive application/store boundary for one page of job history. */
export const MIN_JOB_PAGE_LIMIT = 1;
export const MAX_JOB_PAGE_LIMIT = 100;

/** Validate and narrow a transport/application number before it reaches persistence. */
export function jobPageLimit(value: number): JobPageLimit {
  if (!Number.isInteger(value) || value < MIN_JOB_PAGE_LIMIT || value > MAX_JOB_PAGE_LIMIT) {
    throw new RangeError(
      `Job page limit must be an integer from ${MIN_JOB_PAGE_LIMIT} through ${MAX_JOB_PAGE_LIMIT}.`,
    );
  }
  return value as JobPageLimit;
}

/** Persistence-neutral exclusive position in `(created_at DESC, id DESC)` order. */
export interface JobPageCursor {
  readonly createdAtMs: number;
  readonly id: string;
}

/** One typed keyset request; the first page omits its exclusive cursor. */
export interface JobPageInput {
  readonly limit: JobPageLimit;
  readonly cursor?: JobPageCursor | undefined;
}

/** One bounded page and the exclusive position required to continue it. */
export interface JobSummaryPage {
  readonly jobs: JobSummaryRecord[];
  readonly nextCursor: JobPageCursor | null;
}

export interface AddJobInput {
  projectId: string;
  documentId: string | null;
  kind: string;
  operation: string;
  status: string;
  provider: string;
  model: string;
  requestJson: string;
  resultJson: string;
  error: string | null;
  /** Details of the single event row written with the job. */
  eventDetailsJson: string;
  /** The retried predecessor; null for first-run jobs (#272 retry chain). */
  retryOfJobId?: string | null;
  now: Date;
}

/** A terminal (or failed) outcome transition appended to a running job. */
export interface MarkJobOutcomeInput {
  status: string;
  resultJson?: string | undefined;
  /** Honest post-execution model provenance when the executor resolves it. */
  model?: string | undefined;
  error: string | null;
  eventDetailsJson: string;
  now: Date;
}

export interface AddUsageEventInput {
  projectId: string;
  jobId: string;
  provider: string;
  model: string;
  promptTokens: number;
  completionTokens: number;
  requestEvidenceJson: string;
  now: Date;
}

/** The usage fields of a completed proposal, keyed to its job (#392). */
export type CompletedProposalUsageInput = Omit<AddUsageEventInput, "projectId" | "jobId" | "now">;

/**
 * The atomic completed-proposal landing (#392): the job row and its usage
 * event commit in one transaction, so a crash between the two writes can
 * never leave a completed job without its usage event.
 */
export interface RecordCompletedProposalJobInput {
  job: AddJobInput;
  usage: CompletedProposalUsageInput;
}

/**
 * The atomic retry completion (#392): the terminal outcome transition of an
 * existing running job and its usage event commit in one transaction.
 */
export interface CompleteJobWithUsageInput {
  outcome: MarkJobOutcomeInput;
  usage: CompletedProposalUsageInput;
}
