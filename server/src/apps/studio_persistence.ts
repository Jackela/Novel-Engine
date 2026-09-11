import type { StudioPersistence } from "../contexts/studio/application/studio_services.js";
import { DocumentStorePart } from "../contexts/studio/infrastructure/document_store_part.js";
import { JobStorePart } from "../contexts/studio/infrastructure/job_store_part.js";
import { LoreStorePart } from "../contexts/studio/infrastructure/lore_store_part.js";
import { ProjectStorePart } from "../contexts/studio/infrastructure/project_store_part.js";
import { ProposalAcceptanceStorePart } from "../contexts/studio/infrastructure/proposal_acceptance_store_part.js";
import { ProposalContextStorePart } from "../contexts/studio/infrastructure/proposal_context_store_part.js";
import { ReviewStorePart } from "../contexts/studio/infrastructure/review_store_part.js";
import { VolumeStorePart } from "../contexts/studio/infrastructure/volume_store_part.js";
import type { StudioSqliteDatabase } from "../shared/infrastructure/db/connection.js";

/**
 * Composition-root wiring shared by the API app and the CLI: one focused
 * store part per narrow port, all sharing the caller's database handle.
 * Each application service receives only the parts it actually uses.
 */
export function createStudioPersistence(database: StudioSqliteDatabase): StudioPersistence {
  return {
    projects: new ProjectStorePart(database),
    documents: new DocumentStorePart(database),
    volumes: new VolumeStorePart(database),
    lore: new LoreStorePart(database),
    jobs: new JobStorePart(database),
    reviewOutcomes: new ReviewStorePart(database),
    proposalContext: new ProposalContextStorePart(database),
    proposalAcceptance: new ProposalAcceptanceStorePart(database),
  };
}
