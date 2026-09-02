import { randomUUID } from "node:crypto";
import { link, rename, unlink } from "node:fs/promises";
import { dirname } from "node:path";

import {
  cleanupPublicationSidecars,
  errorCode,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";
import {
  ExportFileEvidenceError,
  matchesFileProof,
  readFileProof,
} from "./export_publication_file_evidence.js";

export interface OwnedArtifactProof extends FileIdentity {
  readonly sizeBytes: number;
  readonly checksumSha256: string;
}

export type OwnedFinalRemoval = "missing" | "removed" | "replacement-restored";

export const REPLACEMENT_PRESERVED_ERROR =
  "Export rollback preserved a replacement and its recovery sidecars for operator review.";

export async function rollbackPublication(
  target: string,
  stage: string,
  manifest: string,
  stagingDirectory: string,
  proof: OwnedArtifactProof,
  manifestIdentity: FileIdentity | undefined,
  afterQuarantine?: (quarantine: string, target: string) => Promise<void>,
): Promise<void> {
  const removal = await removeOwnedFinalViaQuarantine(target, proof, afterQuarantine);
  if (removal === "replacement-restored") throw new Error(REPLACEMENT_PRESERVED_ERROR);
  await cleanupPublicationSidecars(stage, manifest, stagingDirectory, {
    stage: { dev: proof.dev, ino: proof.ino },
    manifest: manifestIdentity,
  });
}

export async function removeOwnedFinalViaQuarantine(
  target: string,
  expected: OwnedArtifactProof,
  afterQuarantine?: (quarantine: string, target: string) => Promise<void>,
): Promise<OwnedFinalRemoval> {
  const quarantine = `${target}.rollback-${randomUUID()}`;
  try {
    await rename(target, quarantine);
  } catch (error) {
    if (isMissingOrReplacedTarget(error)) return "missing";
    throw error;
  }
  await syncDirectory(dirname(target));
  await afterQuarantine?.(quarantine, target);
  const owned = await isExpectedFile(quarantine, expected);
  if (owned) {
    await unlink(quarantine);
    await syncDirectory(dirname(target));
    return "removed";
  }
  // link() is no-clobber: if target is occupied, both that new file and the
  // quarantined replacement remain for explicit recovery/reporting.
  await link(quarantine, target);
  await syncDirectory(dirname(target));
  await unlink(quarantine);
  await syncDirectory(dirname(target));
  return "replacement-restored";
}

async function isExpectedFile(path: string, expected: OwnedArtifactProof): Promise<boolean> {
  try {
    const proof = await readFileProof(path, { missingAllowed: true });
    return (
      proof !== null &&
      proof.dev === expected.dev &&
      proof.ino === expected.ino &&
      matchesFileProof(proof, expected.sizeBytes, expected.checksumSha256)
    );
  } catch (error) {
    if (error instanceof ExportFileEvidenceError) return false;
    throw error;
  }
}

function isMissingOrReplacedTarget(error: unknown): boolean {
  const code = errorCode(error);
  return code === "ENOENT" || code === "ELOOP";
}
