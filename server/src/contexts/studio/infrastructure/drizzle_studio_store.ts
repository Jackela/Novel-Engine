import type { StudioSqliteDatabase } from "../../../shared/infrastructure/db/connection.js";
import type {
  AddDocumentInput,
  AddJobInput,
  AddUsageEventInput,
  AdvanceDocumentInput,
  CaptureReviewSnapshotInput,
  DocumentMatchRecord,
  DocumentWithCurrent,
  EditorialAssessmentRecord,
  JobRecord,
  MarkJobOutcomeInput,
  ProjectScope,
  ProjectUsageAggregate,
  RecordSnapshotReviewInput,
  ReviewSnapshotDocument,
  StudioStore,
} from "../application/ports/studio_store.js";
import type {
  AddVolumeInput,
  AlterVolumeInput,
  PlaceDocumentInput,
} from "../application/ports/volume_store.js";
import { DocumentStorePart } from "./document_store_part.js";
import { JobStorePart } from "./job_store_part.js";
import { ProjectStorePart } from "./project_store_part.js";
import { ReviewStorePart } from "./review_store_part.js";
import { VolumeStorePart } from "./volume_store_part.js";

export interface DrizzleStudioStoreOptions {
  database: StudioSqliteDatabase;
  /** Data directory owning `novel-engine.sqlite3`; export trees live beneath it. */
  dataDirectory: string;
}

/**
 * Drizzle implementation of the authoring StudioStore. Project, document,
 * revision/FTS, and workflow-job persistence each stay in a focused part.
 */
export class DrizzleStudioStore extends ProjectStorePart implements StudioStore {
  private readonly documentStore: DocumentStorePart;
  private readonly volumeStore: VolumeStorePart;
  private readonly editorialReviews: ReviewStorePart;
  private readonly workflowJobs: JobStorePart;

  constructor(options: DrizzleStudioStoreOptions) {
    super(options.database, options.dataDirectory);
    this.documentStore = new DocumentStorePart(options.database);
    this.volumeStore = new VolumeStorePart(options.database);
    this.editorialReviews = new ReviewStorePart(options.database);
    this.workflowJobs = new JobStorePart(options.database);
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

  addUsageEvent(scope: ProjectScope, input: AddUsageEventInput): void {
    this.workflowJobs.addUsageEvent(scope, input);
  }

  aggregateProjectUsage(scope: ProjectScope, projectId: string): ProjectUsageAggregate {
    return this.workflowJobs.aggregateProjectUsage(scope, projectId);
  }

  findJob(scope: ProjectScope, projectId: string, jobId: string): JobRecord {
    return this.workflowJobs.findJob(scope, projectId, jobId);
  }

  collectProjectJobs(scope: ProjectScope, projectId: string): JobRecord[] {
    return this.workflowJobs.collectProjectJobs(scope, projectId);
  }

  markJobOutcome(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    input: MarkJobOutcomeInput,
  ): JobRecord {
    return this.workflowJobs.markJobOutcome(scope, projectId, jobId, input);
  }

  setJobResult(
    scope: ProjectScope,
    projectId: string,
    jobId: string,
    resultJson: string,
    now: Date,
  ): JobRecord {
    return this.workflowJobs.setJobResult(scope, projectId, jobId, resultJson, now);
  }

  captureReviewSnapshot(
    scope: ProjectScope,
    projectId: string,
    input: CaptureReviewSnapshotInput,
  ): { snapshotId: string; documents: ReviewSnapshotDocument[] } {
    return this.editorialReviews.captureReviewSnapshot(scope, projectId, input);
  }

  recordSnapshotReview(
    scope: ProjectScope,
    projectId: string,
    input: RecordSnapshotReviewInput,
  ): EditorialAssessmentRecord {
    return this.editorialReviews.recordSnapshotReview(scope, projectId, input);
  }

  listEditorialAssessments(scope: ProjectScope, projectId: string): EditorialAssessmentRecord[] {
    return this.editorialReviews.listEditorialAssessments(scope, projectId);
  }
}
