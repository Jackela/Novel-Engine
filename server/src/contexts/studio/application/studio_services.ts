import type { TextGenerationProviderFactory } from "../../../contexts/ai/application/ports/text_generation.js";
import { BeatAssociationService } from "./beat_association_service.js";
import { DocumentService } from "./document_service.js";
import { type ExportArtifactGateway, SnapshotArtifactService } from "./export_artifact_service.js";
import { ImportService } from "./import_service.js";
import { JobHistoryService } from "./job_history_service.js";
import { LoreAliasService } from "./lore_alias_service.js";
import { InFlightOperationGuard, type OperationCapacityPolicy } from "./operation_in_flight.js";
import type { DocumentStore } from "./ports/document_store.js";
import type { ExportOutcomeStore } from "./ports/export_store.js";
import type { StudioJobLedgerStore } from "./ports/job_ledger_store.js";
import type { LegacyWorkspaceReader } from "./ports/legacy_workspace_reader.js";
import type { StudioLoreStore } from "./ports/lore_store.js";
import type { ProjectArtifactCleaner } from "./ports/project_artifact_cleaner.js";
import type { ProjectStore } from "./ports/project_store.js";
import type { ProposalAcceptanceStore } from "./ports/proposal_acceptance_store.js";
import type { ProposalContextStore } from "./ports/proposal_context_store.js";
import type { ReviewOutcomeStore } from "./ports/review_outcome_store.js";
import type { StudioVolumeStore } from "./ports/volume_store.js";
import { ProjectService } from "./project_service.js";
import { ProposalGenerationPipeline } from "./proposal_pipeline.js";
import { AiProposalService } from "./proposal_service.js";
import { type ReviewProviderProvenance, ReviewService } from "./review_service.js";
import { RevisionService } from "./revision_service.js";
import { VolumeService } from "./volume_service.js";

/** The per-capability service graph handed to the studio HTTP surface. */
export interface StudioServices {
  projects: ProjectService;
  documents: DocumentService;
  volumes: VolumeService;
  beats: BeatAssociationService;
  lore: LoreAliasService;
  revisions: RevisionService;
  proposals: AiProposalService;
  reviewAssessments: ReviewService;
  artifacts: SnapshotArtifactService;
  imports: ImportService;
  jobHistory: JobHistoryService;
}

/**
 * The studio persistence boundary: one narrow store port per focused part.
 * The composition root instantiates the concrete parts over one database
 * handle and distributes them here; each service declares only the parts it
 * actually uses.
 */
export interface StudioPersistence {
  projects: ProjectStore;
  documents: DocumentStore;
  volumes: StudioVolumeStore;
  lore: StudioLoreStore;
  jobs: StudioJobLedgerStore;
  reviewOutcomes: ReviewOutcomeStore;
  proposalContext: ProposalContextStore;
  proposalAcceptance: ProposalAcceptanceStore;
}

export interface CreateStudioServicesOptions {
  now?: (() => Date) | undefined;
  /** Per-request provider factory; the composition root injects the concrete one. */
  providerFactory: TextGenerationProviderFactory;
  /** Server-owned review provenance; model choice is never an HTTP input. */
  reviewProvenance?: ReviewProviderProvenance | undefined;
  /** Export snapshots and artifact records have a focused persistence boundary. */
  artifactStore: ExportOutcomeStore;
  /** Filesystem adapter for atomic artifact writes and confined retrieval. */
  artifactFiles: ExportArtifactGateway;
  /** Post-commit cleanup for one deleted project's secondary export tree. */
  projectArtifactCleaner: ProjectArtifactCleaner;
  /** Read-only legacy workspace access; the composition root injects the FS adapter. */
  legacyWorkspaceReader: LegacyWorkspaceReader;
  /** Lorebook injection budget (#445); undefined keeps the adjudicated default. */
  loreBudgetCharacters?: number | undefined;
  /** App-local admission limits for expensive Studio workflows. */
  operationCapacity?: OperationCapacityPolicy | undefined;
}

export function createStudioServices(
  persistence: StudioPersistence,
  options: CreateStudioServicesOptions,
): StudioServices {
  const now = options.now ?? (() => new Date());
  // One guard per app instance: it serializes identical in-flight pipeline
  // operations (#305) across the proposal and export/retry surfaces.
  const inFlight = new InFlightOperationGuard(options.operationCapacity);
  // The proposal generation pipeline, constructed once: it owns the prompt
  // and landing configuration (#445) and the execution sequence shared by the
  // synchronous draft, the SSE twin, and the retry path.
  const proposals = new ProposalGenerationPipeline(
    persistence.proposalContext,
    persistence.jobs,
    options.providerFactory,
    inFlight,
    now,
    options.loreBudgetCharacters,
  );
  const documents = new DocumentService(persistence.documents, persistence.volumes, now);
  const reviewAssessments = new ReviewService(persistence.reviewOutcomes, {
    now,
    provenance: options.reviewProvenance,
    providerFactory: options.providerFactory,
  });
  const artifacts = new SnapshotArtifactService(options.artifactStore, options.artifactFiles, {
    now,
  });
  return {
    projects: new ProjectService(persistence.projects, persistence.volumes, now, {
      inFlight,
      artifactCleaner: options.projectArtifactCleaner,
    }),
    documents,
    volumes: new VolumeService(persistence.volumes, now),
    beats: new BeatAssociationService(persistence.documents, now),
    lore: new LoreAliasService(persistence.documents, persistence.lore, now),
    revisions: new RevisionService(persistence.documents, documents),
    proposals: new AiProposalService(persistence.proposalAcceptance, proposals, now),
    reviewAssessments,
    artifacts,
    jobHistory: new JobHistoryService(
      persistence.jobs,
      persistence.reviewOutcomes,
      reviewAssessments,
      artifacts,
      {
        now,
        inFlight,
        proposals,
      },
    ),
    imports: new ImportService(persistence.projects, options.legacyWorkspaceReader, now),
  };
}
