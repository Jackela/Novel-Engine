import type { ArtifactFileEvidence } from "../application/ports/artifact_gateway.js";
import type { ExportArtifactFormat } from "../application/ports/export_store.js";
import {
  buildPublicationEvidence,
  compensateFailedPublication,
  EXPORT_PUBLICATION_VERSION,
  preparePublication,
  stagePublicationFiles,
} from "./export_artifact_publication_stages.js";
import type { ExportPublicationCleanupJournal } from "./export_publication_cleanup_journal.js";

export { EXPORT_PUBLICATION_VERSION };

/** Durable recovery manifest retained until the outcome's file cleanup converges. */
export interface ExportPublicationManifest {
  readonly version: typeof EXPORT_PUBLICATION_VERSION;
  readonly publication_id: string;
  readonly artifact_id: string;
  readonly project_id: string;
  readonly format: ExportArtifactFormat;
  readonly relative_path: string;
  readonly stage_file: string;
  readonly size_bytes: number;
  readonly checksum_sha256: string;
}

export interface ArtifactPublicationInput {
  readonly projectDirectory: string;
  readonly target: string;
  readonly relativePath: string;
  readonly projectId: string;
  readonly artifactId: string;
  readonly format: ExportArtifactFormat;
  readonly contents: Buffer;
  readonly reportCleanupFailure?: ((failure: unknown) => void) | undefined;
  /** Deterministic publication/temporary ids used only by collision tests. */
  readonly newId?: (() => string) | undefined;
  /** Deterministic shared-staging race seam used only by filesystem tests. */
  readonly afterStagingReady?: (() => Promise<void>) | undefined;
  /** Deterministic staged-descriptor mutation seam used only by capacity tests. */
  readonly afterStageWrite?: ((stage: string) => Promise<void>) | undefined;
  /** Deterministic race seam used only by filesystem rollback tests. */
  readonly afterRollbackQuarantine?:
    | ((quarantine: string, target: string) => Promise<void>)
    | undefined;
  readonly cleanupJournal?: ExportPublicationCleanupJournal | undefined;
}

/**
 * Publishes durable bytes plus a recovery manifest before database landing.
 * The stage hard-link remains until acknowledge(), making every crash window
 * recoverable from the database row as the commit marker.
 */
export async function publishArtifact(
  input: ArtifactPublicationInput,
): Promise<ArtifactFileEvidence> {
  const prepared = await preparePublication(input);
  try {
    const staged = await stagePublicationFiles(input, prepared);
    return buildPublicationEvidence(input, prepared, staged);
  } catch (error) {
    await compensateFailedPublication(input, prepared);
    throw error;
  }
}
