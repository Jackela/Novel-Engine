import type { TextGenerationProviderFactory } from "../../../contexts/ai/application/ports/text_generation.js";
import { DocumentService } from "./document_service.js";
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
}

export interface CreateStudioServicesOptions {
  now?: (() => Date) | undefined;
  /** Per-request provider factory; the composition root injects the concrete one. */
  providerFactory: TextGenerationProviderFactory;
  /** Server-owned review provenance; model choice is never an HTTP input. */
  reviewProvenance?: ReviewProviderProvenance | undefined;
}

export function createStudioServices(
  store: StudioStore,
  options: CreateStudioServicesOptions,
): StudioServices {
  const now = options.now ?? (() => new Date());
  const documents = new DocumentService(store, now);
  return {
    projects: new ProjectService(store, now),
    documents,
    revisions: new RevisionService(store, documents),
    proposals: new AiProposalService(store, documents, options.providerFactory, now),
    reviewAssessments: new ReviewService(store, { now, provenance: options.reviewProvenance }),
  };
}
