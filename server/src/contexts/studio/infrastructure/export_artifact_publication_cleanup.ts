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

// Mutable progress shared by the cleanup steps below: which compensating side
// effects already happened and whether the outcome stayed clean, mirroring the
// PreparedArtifactPublication trackers used by the staging steps.
interface FailedPublicationCleanupProgress {
  cleanupIntentRecorded: boolean;
  preserveRecoveryEvidence: boolean;
  cleanupSucceeded: boolean;
}

export async function cleanupFailedPublication(input: FailedPublicationCleanup): Promise<void> {
  const progress: FailedPublicationCleanupProgress = {
    cleanupIntentRecorded: input.cleanupIntentRecorded,
    preserveRecoveryEvidence: false,
    cleanupSucceeded: true,
  };
  await beginFailedPublicationCleanupIntent(input, progress);
  await removeFailedPublicationFinal(input, progress);
  await removeFailedPublicationSidecars(input, progress);
  await completeFailedPublicationCleanup(input, progress);
}

// Step 1: record the cleanup intent for this publication when it is not on
// file yet; a failure here keeps recovery evidence for crash recovery.
async function beginFailedPublicationCleanupIntent(
  input: FailedPublicationCleanup,
  progress: FailedPublicationCleanupProgress,
): Promise<void> {
  if (
    !progress.cleanupIntentRecorded &&
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
      progress.cleanupIntentRecorded = true;
    } catch (failure) {
      progress.preserveRecoveryEvidence = true;
      reportWithoutMasking(failure, input.reportCleanupFailure);
    }
  }
}

// Step 2: quarantine-remove the linked final and sync the project directory;
// a preserved replacement or removal failure keeps recovery evidence.
async function removeFailedPublicationFinal(
  input: FailedPublicationCleanup,
  progress: FailedPublicationCleanupProgress,
): Promise<void> {
  if (input.finalLinked && input.stageIdentity !== undefined) {
    try {
      const removal = await removeOwnedFinalViaQuarantine(
        input.target,
        input.artifactProof,
        input.afterRollbackQuarantine,
      );
      if (removal === "replacement-restored") {
        progress.preserveRecoveryEvidence = true;
        reportWithoutMasking(new Error(REPLACEMENT_PRESERVED_ERROR), input.reportCleanupFailure);
      }
    } catch (failure) {
      progress.preserveRecoveryEvidence = true;
      reportWithoutMasking(failure, input.reportCleanupFailure);
    }
    progress.cleanupSucceeded =
      (await cleanupWithoutMasking(
        syncDirectory(input.projectDirectory),
        input.reportCleanupFailure,
      )) && progress.cleanupSucceeded;
  }
}

// Step 3: remove the manifest temporary and the publication sidecars unless
// preserved recovery evidence must stay behind.
async function removeFailedPublicationSidecars(
  input: FailedPublicationCleanup,
  progress: FailedPublicationCleanupProgress,
): Promise<void> {
  if (!progress.preserveRecoveryEvidence) {
    progress.cleanupSucceeded =
      (await cleanupWithoutMasking(
        cleanupOwnedFile(input.manifestTemporary, input.manifestTemporaryIdentity),
        input.reportCleanupFailure,
      )) && progress.cleanupSucceeded;
    progress.cleanupSucceeded =
      (await cleanupWithoutMasking(
        cleanupPublicationSidecars(input.stage, input.manifest, input.stagingDirectory, {
          stage: input.stageIdentity,
          manifest: input.manifestIdentity,
        }),
        input.reportCleanupFailure,
      )) && progress.cleanupSucceeded;
  }
}

// Step 4: complete the cleanup journal only when the intent was recorded and
// every cleanup step succeeded without preserved recovery evidence.
async function completeFailedPublicationCleanup(
  input: FailedPublicationCleanup,
  progress: FailedPublicationCleanupProgress,
): Promise<void> {
  if (
    progress.cleanupIntentRecorded &&
    progress.cleanupSucceeded &&
    !progress.preserveRecoveryEvidence &&
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
