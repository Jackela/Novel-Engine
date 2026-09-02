import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type { JobPageInput, JobSummaryPage } from "../application/ports/job_records.js";
import type { SetLoreAliasesInput, SetLoreStatusInput } from "../application/ports/lore_store.js";
import type {
  AddDocumentInput,
  AddJobInput,
  AddUsageEventInput,
  AdvanceDocumentInput,
  ClaimJobRetryInput,
  CompleteJobWithUsageInput,
  DocumentMatchRecord,
  DocumentWithCurrent,
  EditorialAssessmentRecord,
  EvaluatedReview,
  JobRecord,
  JobRetryClaim,
  MarkJobOutcomeInput,
  ProjectScope,
  ProjectUsageAggregate,
  RecordCompletedProposalJobInput,
  ReviewCompletionRecord,
  ReviewSource,
  StudioStore,
} from "../application/ports/studio_store.js";
import type {
  AddVolumeInput,
  AlterVolumeInput,
  PlaceDocumentInput,
} from "../application/ports/volume_store.js";
import { DocumentStorePart } from "./document_store_part.js";
import { JobStorePart } from "./job_store_part.js";
import { LoreStorePart } from "./lore_store_part.js";
import { ProjectStorePart } from "./project_store_part.js";
import { ProposalAcceptanceStorePart } from "./proposal_acceptance_store_part.js";
import { ReviewStorePart } from "./review_store_part.js";
import { VolumeStorePart } from "./volume_store_part.js";

export interface DrizzleStudioStoreOptions {
  database: StudioSqliteDatabase;
}

/**
 * Drizzle implementation of the authoring StudioStore. Project, document,
 * revision/FTS, and workflow-job persistence each stay in a focused part.
 */
export class DrizzleStudioStore extends ProjectStorePart implements StudioStore {
  private readonly documentStore: DocumentStorePart;
  private readonly volumeStore: VolumeStorePart;
  private readonly editorialReviews: ReviewStorePart;
  private readonly proposalAcceptance: ProposalAcceptanceStorePart;
  private readonly workflowJobs: JobStorePart;
  private readonly loreKeys: LoreStorePart;

  constructor(options: DrizzleStudioStoreOptions) {
    super(options.database);
    this.documentStore = new DocumentStorePart(options.database);
    this.volumeStore = new VolumeStorePart(options.database);
    this.editorialReviews = new ReviewStorePart(options.database);
    this.proposalAcceptance = new ProposalAcceptanceStorePart(options.database);
    this.workflowJobs = new JobStorePart(options.database);
    this.loreKeys = new LoreStorePart(options.database);
  }

  findVolumes(scope: ProjectScope, projectId: string) {
    return this.volumeStore.findVolumes(scope, projectId);
  }

  addVolume(scope: ProjectScope, projectId: string, input: AddVolumeInput) {
    return this.volumeStore.addVolume(scope, projectId, input);
  }

  alterVolume(scope: ProjectScope, projectId: string, volumeId: string, input: AlterVolumeInput) {
    return this.volumeStore.alterVolume(scope, projectId, volumeId, input);
  }

  dropVolume(scope: ProjectScope, projectId: string, volumeId: string): void {
    this.volumeStore.dropVolume(scope, projectId, volumeId);
  }

  placeDocumentInVolume(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: PlaceDocumentInput,
  ) {
    return this.volumeStore.placeDocumentInVolume(scope, projectId, documentId, input);
  }

  renumberVolumes(scope: ProjectScope, projectId: string, volumeIds: string[], now: Date) {
    return this.volumeStore.renumberVolumes(scope, projectId, volumeIds, now);
  }

  findDocuments(scope: ProjectScope, projectId: string): DocumentWithCurrent[] {
    return this.documentStore.findDocuments(scope, projectId);
  }

  findDocument(scope: ProjectScope, projectId: string, documentId: string): DocumentWithCurrent {
    return this.documentStore.findDocument(scope, projectId, documentId);
  }

  addDocument(
    scope: ProjectScope,
    projectId: string,
    input: AddDocumentInput,
  ): DocumentWithCurrent {
    return this.documentStore.addDocument(scope, projectId, input);
  }

  advanceDocument(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: AdvanceDocumentInput,
  ): DocumentWithCurrent {
    return this.documentStore.advanceDocument(scope, projectId, documentId, input);
  }

  dropDocument(scope: ProjectScope, projectId: string, documentId: string): void {
    this.documentStore.dropDocument(scope, projectId, documentId);
  }

  setBeatReference(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: { beatRef: string | null; now: Date },
  ): DocumentWithCurrent {
    return this.documentStore.setBeatReference(scope, projectId, documentId, input);
  }

  setLoreAliases(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreAliasesInput,
  ): DocumentWithCurrent {
    return this.loreKeys.setLoreAliases(scope, projectId, documentId, input);
  }

  setLoreStatus(
    scope: ProjectScope,
    projectId: string,
    documentId: string,
    input: SetLoreStatusInput,
  ): DocumentWithCurrent {
    return this.loreKeys.setLoreStatus(scope, projectId, documentId, input);
  }

  renumberDocuments(
    scope: ProjectScope,
    projectId: string,
    documentIds: string[],
    now: Date,
  ): DocumentWithCurrent[] {
    // The reorder projection is a reading-order behavior owned by the
    // volume part (ADR-0005); it mutates only document positions.
    return this.volumeStore.renumberDocuments(scope, projectId, documentIds, now);
  }

  nextPosition(scope: ProjectScope, projectId: string, kind: string, volumeId?: string | null) {
    return this.documentStore.nextPosition(scope, projectId, kind, volumeId);
  }

  findRevisions(scope: ProjectScope, projectId: string, documentId: string) {
    return this.documentStore.findRevisions(scope, projectId, documentId);
  }

  findRevision(scope: ProjectScope, projectId: string, documentId: string, revisionId: string) {
    return this.documentStore.findRevision(scope, projectId, documentId, revisionId);
  }

  matchProjectDocuments(
    scope: ProjectScope,
    projectId: string,
    matchQuery: string,
  ): DocumentMatchRecord[] {
    return this.documentStore.matchProjectDocuments(scope, projectId, matchQuery);
  }

  addJob(scope: ProjectScope, input: AddJobInput): JobRecord {
    return this.workflowJobs.addJob(scope, input);
  }

  findJobRetry(
    scope: ProjectScope,
    projectId: string,
    sourceJobId: string,
    requestKey: string,
  ): JobRecord | null {
    return this.workflowJobs.findJobRetry(scope, projectId, sourceJobId, requestKey);
  }

  claimJobRetry(scope: ProjectScope, input: ClaimJobRetryInput): JobRetryClaim {
    return this.workflowJobs.claimJobRetry(scope, input);
  }

  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void {
    this.workflowJobs.addUsageEvent(scope, input);
  }

  recordCompletedProposalJob(
    scope: ProjectScope,
    input: RecordCompletedProposalJobInput,
  ): JobRecord {
    return this.workflowJobs.recordCompletedProposalJob(scope, input);
  }

  markJobOutcomeWithUsage(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: CompleteJobWithUsageInput,
  ): JobRecord {
    return this.workflowJobs.markJobOutcomeWithUsage(scope, projectId, jobId, input);
  }

  aggregateProjectUsage(scope: ProjectScope, projectId: string, now: Date): ProjectUsageAggregate {
    return this.workflowJobs.aggregateProjectUsage(scope, projectId, now);
  }

  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord {
    return this.workflowJobs.findJob(scope, projectId, jobId);
  }

  collectProjectJobSummaries(
    scope: ProjectScope,
    projectId: string,
    input: JobPageInput,
  ): JobSummaryPage {
    return this.workflowJobs.collectProjectJobSummaries(scope, projectId, input);
  }

  markJobOutcome(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: MarkJobOutcomeInput,
  ): JobRecord {
    return this.workflowJobs.markJobOutcome(scope, projectId, jobId, input);
  }

  acceptCompletedProposal(scope: ProjectScope, projectId: string, jobId: string, now: Date) {
    return this.proposalAcceptance.acceptCompletedProposal(scope, projectId, jobId, now);
  }

  readReviewSource(scope: ProjectScope, projectId: string, capturedAt: Date): ReviewSource {
    return this.editorialReviews.readReviewSource(scope, projectId, capturedAt);
  }

  recordCompletedReviewJob(scope: ProjectScope, input: EvaluatedReview): ReviewCompletionRecord {
    return this.editorialReviews.recordCompletedReviewJob(scope, input);
  }

  completeReviewRetryJob(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: EvaluatedReview,
  ): ReviewCompletionRecord {
    return this.editorialReviews.completeReviewRetryJob(scope, projectId, jobId, input);
  }

  listEditorialAssessments(scope: ProjectScope, projectId: string): EditorialAssessmentRecord[] {
    return this.editorialReviews.listEditorialAssessments(scope, projectId);
  }
}
