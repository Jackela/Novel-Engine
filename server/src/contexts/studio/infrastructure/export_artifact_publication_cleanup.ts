import {
  cleanupOwnedFile,
  cleanupPublicationSidecars,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";
import type { ExportPublicationManifest } from "./export_artifact_publication.js";
import {
  type OwnedArtifactProof,
  REPLACEMENT_PRESERVED_ERROR,
  removeOwnedFinalViaQuarantine,
} from "./export_artifact_rollback.js";
import type {
  ExportPublicationCleanupJournal,
  PublicationCleanupIntent,
} from "./export_publication_cleanup_journal.js";

interface FailedPublicationCleanup {
  readonly target: string;
  readonly projectDirectory: string;
  readonly stage: string;
  readonly manifest: string;
  readonly manifestTemporary: string;
  readonly stagingDirectory: string;
  readonly artifactProof: OwnedArtifactProof;
  readonly finalLinked: boolean;
  readonly stageIdentity: FileIdentity | undefined;
  readonly manifestIdentity: FileIdentity | undefined;
  readonly manifestTemporaryIdentity: FileIdentity | undefined;
  readonly record: ExportPublicationManifest | undefined;
  readonly cleanupJournal: ExportPublicationCleanupJournal | undefined;
  readonly cleanupIntentRecorded: boolean;
  readonly reportCleanupFailure: ((failure: unknown) => void) | undefined;
  readonly afterRollbackQuarantine:
    | ((quarantine: string, target: string) => Promise<void>)
    | undefined;
}

export async function cleanupFailedPublication(input: FailedPublicationCleanup): Promise<void> {
  let preserveRecoveryEvidence = false;
  let cleanupIntentRecorded = input.cleanupIntentRecorded;
  if (
    !cleanupIntentRecorded &&
    input.record !== undefined &&
    input.manifestIdentity !== undefined &&
    input.cleanupJournal !== undefined
  ) {
    try {
      if (input.stageIdentity === undefined) {
        throw new Error("Export cleanup intent is missing its staged file identity.");
      }
      await input.cleanupJournal.begin({
        manifest: input.record,
        stageIdentity: input.stageIdentity,
        manifestIdentity: input.manifestIdentity,
      });
      cleanupIntentRecorded = true;
    } catch (failure) {
      preserveRecoveryEvidence = true;
      reportWithoutMasking(failure, input.reportCleanupFailure);
    }
  }
  let cleanupSucceeded = true;
  if (input.finalLinked && input.stageIdentity !== undefined) {
    try {
      const removal = await removeOwnedFinalViaQuarantine(
        input.target,
        input.artifactProof,
        input.afterRollbackQuarantine,
      );
      if (removal === "replacement-restored") {
        preserveRecoveryEvidence = true;
        reportWithoutMasking(new Error(REPLACEMENT_PRESERVED_ERROR), input.reportCleanupFailure);
      }
    } catch (failure) {
      preserveRecoveryEvidence = true;
      reportWithoutMasking(failure, input.reportCleanupFailure);
    }
    cleanupSucceeded =
      (await cleanupWithoutMasking(
        syncDirectory(input.projectDirectory),
        input.reportCleanupFailure,
      )) && cleanupSucceeded;
  }
  if (!preserveRecoveryEvidence) {
    cleanupSucceeded =
      (await cleanupWithoutMasking(
        cleanupOwnedFile(input.manifestTemporary, input.manifestTemporaryIdentity),
        input.reportCleanupFailure,
      )) && cleanupSucceeded;
    cleanupSucceeded =
      (await cleanupWithoutMasking(
        cleanupPublicationSidecars(input.stage, input.manifest, input.stagingDirectory, {
          stage: input.stageIdentity,
          manifest: input.manifestIdentity,
        }),
        input.reportCleanupFailure,
      )) && cleanupSucceeded;
  }
  if (
    cleanupIntentRecorded &&
    cleanupSucceeded &&
    !preserveRecoveryEvidence &&
    input.record !== undefined
  ) {
    await cleanupWithoutMasking(
      input.cleanupJournal?.complete(input.record.publication_id) ?? Promise.resolve(),
      input.reportCleanupFailure,
    );
  }
}

export async function cleanupWithIntent(
  journal: ExportPublicationCleanupJournal | undefined,
  intent: PublicationCleanupIntent,
  cleanup: () => Promise<void>,
): Promise<void> {
  if (journal === undefined) return cleanup();
  await journal.begin(intent);
  await cleanup();
  await journal.complete(intent.manifest.publication_id);
}

async function cleanupWithoutMasking(
  promise: Promise<unknown>,
  reportCleanupFailure?: (failure: unknown) => void,
): Promise<boolean> {
  try {
    await promise;
    return true;
  } catch (failure) {
    reportWithoutMasking(failure, reportCleanupFailure);
    return false;
  }
}

function reportWithoutMasking(
  failure: unknown,
  reportCleanupFailure?: (failure: unknown) => void,
): void {
  try {
    reportCleanupFailure?.(failure);
  } catch {
    // Cleanup reporting is secondary and cannot replace publication failure.
  }
}
