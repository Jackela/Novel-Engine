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
