import type { TextGenerationProviderFactory } from "../../../contexts/ai/application/ports/text_generation.js";
import { DocumentService } from "./document_service.js";
import { type ExportArtifactGateway, SnapshotArtifactService } from "./export_artifact_service.js";
import { ImportService } from "./import_service.js";
import { JobHistoryService } from "./job_history_service.js";
import type { ExportStore } from "./ports/export_store.js";
import type { LegacyWorkspaceReader } from "./ports/legacy_workspace_reader.js";
import type { StudioStore } from "./ports/studio_store.js";
import { ProjectService } from "./project_service.js";
import { AiProposalService } from "./proposal_service.js";
import { type ReviewProviderProvenance, ReviewService } from "./review_service.js";
import { RevisionService } from "./revision_service.js";

/** The per-capability service graph handed to the studio HTTP surface. */
export interface StudioServices {
  projects: ProjectService;
  documents: DocumentService;
  revisions: RevisionService;
  proposals: AiProposalService;
  reviewAssessments: ReviewService;
  artifacts: SnapshotArtifactService;
  imports: ImportService;
  jobHistory: JobHistoryService;
}

export interface CreateStudioServicesOptions {
  now?: (() => Date) | undefined;
  /** Per-request provider factory; the composition root injects the concrete one. */
  providerFactory: TextGenerationProviderFactory;
  /** Server-owned review provenance; model choice is never an HTTP input. */
  reviewProvenance?: ReviewProviderProvenance | undefined;
  /** Export snapshots and artifact records have a focused persistence boundary. */
  artifactStore: ExportStore;
  /** Filesystem adapter for atomic artifact writes and confined retrieval. */
  artifactFiles: ExportArtifactGateway;
  /** Read-only legacy workspace access; the composition root injects the FS adapter. */
  legacyWorkspaceReader: LegacyWorkspaceReader;
}

export function createStudioServices(
  store: StudioStore,
  options: CreateStudioServicesOptions,
): StudioServices {
  const now = options.now ?? (() => new Date());
  const documents = new DocumentService(store, now);
  const reviewAssessments = new ReviewService(store, { now, provenance: options.reviewProvenance });
  const artifacts = new SnapshotArtifactService(
    options.artifactStore,
    store,
    options.artifactFiles,
    {
      now,
    },
  );
  return {
    projects: new ProjectService(store, now),
    documents,
    revisions: new RevisionService(store, documents),
    proposals: new AiProposalService(store, documents, options.providerFactory, now),
    reviewAssessments,
    artifacts,
    jobHistory: new JobHistoryService(store, reviewAssessments, artifacts, {
      now,
      providerFactory: options.providerFactory,
    }),
    imports: new ImportService(store, options.legacyWorkspaceReader, now),
  };
}
