import { link, lstat, readdir, realpath } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";

import {
  assertCanonicalExportArtifactEvidence,
  exportArtifactFilename,
} from "../application/export_artifact_identity.js";
import type { exports as exportArtifacts } from "./db/schema.js";
import {
  cleanupOwnedFile,
  errorCode,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";
import type { ExportPublicationManifest } from "./export_artifact_publication.js";
import {
  assertFileProof,
  type FileProof,
  matchesFileProof,
  readFileProof,
} from "./export_publication_file_evidence.js";

export type ArtifactRow = typeof exportArtifacts.$inferSelect;
export interface MutableRecoveryReport {
  manifestsReconciled: number;
  committedArtifactsVerified: number;
  finalsRestored: number;
  orphanFilesRemoved: number;
  sidecarsRemoved: number;
  deletedProjectDirectoriesRemoved: number;
}

export interface CleanupFileOwnership {
  readonly stage: FileIdentity;
  readonly manifest: FileIdentity;
}

export async function reconcileManifest(
  manifestPath: string | undefined,
  manifestIdentity: FileIdentity | undefined,
  cleanupOwnership: CleanupFileOwnership | undefined,
  stagePath: string | undefined,
  projectDirectory: string,
  manifest: ExportPublicationManifest,
  artifact: ArtifactRow | undefined,
  report: MutableRecoveryReport,
): Promise<boolean> {
  const { finalPath, stage, final } = await preflightManifestRecovery(
    manifestIdentity,
    cleanupOwnership,
    stagePath,
    projectDirectory,
    manifest,
    artifact,
  );
  if (artifact === undefined) {
    if (stage === null && final === null) {
      if (manifestPath !== undefined && manifestIdentity !== undefined) {
        await cleanupOwnedFile(manifestPath, manifestIdentity);
        report.sidecarsRemoved += 1;
      }
      report.manifestsReconciled += 1;
      return true;
    }
    if (final !== null) {
      await cleanupOwnedFile(finalPath, { dev: final.dev, ino: final.ino });
      report.orphanFilesRemoved += 1;
    }
    if (stagePath !== undefined && stage !== null) {
      await cleanupOwnedFile(stagePath, { dev: stage.dev, ino: stage.ino });
      report.sidecarsRemoved += 1;
    }
    if (manifestPath !== undefined && manifestIdentity !== undefined) {
      await cleanupOwnedFile(manifestPath, manifestIdentity);
      report.sidecarsRemoved += 1;
    }
  } else {
    if (final === null) {
      if (stagePath === undefined || stage === null) throw missingArtifact(artifact.id);
      await link(stagePath, finalPath);
      await syncDirectory(projectDirectory);
      report.finalsRestored += 1;
    }
    if (stagePath !== undefined && stage !== null) {
      await cleanupOwnedFile(stagePath, { dev: stage.dev, ino: stage.ino });
      report.sidecarsRemoved += 1;
    }
    if (manifestPath !== undefined && manifestIdentity !== undefined) {
      await cleanupOwnedFile(manifestPath, manifestIdentity);
      report.sidecarsRemoved += 1;
    }
  }
  report.manifestsReconciled += 1;
  return cleanupOwnership !== undefined;
}

export async function preflightManifestRecovery(
  manifestIdentity: FileIdentity | undefined,
  cleanupOwnership: CleanupFileOwnership | undefined,
  stagePath: string | undefined,
  projectDirectory: string,
  manifest: ExportPublicationManifest,
  artifact: ArtifactRow | undefined,
): Promise<{
  readonly finalPath: string;
  readonly stage: FileProof | null;
  readonly final: FileProof | null;
}> {
  const finalPath = resolve(projectDirectory, manifestFilename(manifest));
  const stage = stagePath === undefined ? null : await readFileProof(stagePath);
  const final = await readFileProof(finalPath, true);
  if (cleanupOwnership !== undefined) {
    if (manifestIdentity !== undefined) {
      assertIdentity(manifestIdentity, cleanupOwnership.manifest, "manifest");
    }
    if (stage !== null) {
      assertIdentity({ dev: stage.dev, ino: stage.ino }, cleanupOwnership.stage, "stage");
    }
    if (final !== null) {
      assertIdentity({ dev: final.dev, ino: final.ino }, cleanupOwnership.stage, "final");
    }
  }
  if (artifact === undefined) {
    if (cleanupOwnership === undefined) {
      if (stage === null && final === null) {
        throw new Error(
          `Unproven export manifest requires operator recovery: ${manifest.artifact_id}`,
        );
      }
      throw new Error(`Export cleanup intent is missing for ${manifest.artifact_id}.`);
    }
    if (stage !== null) assertFileProof(stage, manifest.size_bytes, manifest.checksum_sha256);
    if (final !== null) {
      assertFileProof(final, manifest.size_bytes, manifest.checksum_sha256);
      if (stage === null || stage.dev !== final.dev || stage.ino !== final.ino) {
        throw new Error(`Uncommitted export ${manifest.artifact_id} was replaced.`);
      }
    }
  } else {
    assertManifestMatchesArtifact(manifest, artifact);
    if (stage !== null) assertFileProof(stage, artifact.sizeBytes, artifact.checksumSha256);
    if (final !== null) assertFileProof(final, artifact.sizeBytes, artifact.checksumSha256);
    if (stage !== null && final !== null && (stage.dev !== final.dev || stage.ino !== final.ino)) {
      throw new Error(`Committed export ${artifact.id} stage or final was replaced.`);
    }
    if (stage === null && final === null) throw missingArtifact(artifact.id);
  }
  return { finalPath, stage, final };
}

function assertIdentity(actual: FileIdentity, expected: FileIdentity, label: string): void {
  if (actual.dev !== expected.dev || actual.ino !== expected.ino) {
    throw new Error(`Export cleanup ${label} identity was replaced.`);
  }
}

/** Proves that a rollback quarantine is the same staged publication inode. */
export async function ownedPublicationIdentity(
  stagePath: string,
  candidatePath: string,
  size: number,
  checksum: string,
): Promise<FileIdentity | undefined> {
  const stage = await readFileProof(stagePath, true);
  const candidate = await readFileProof(candidatePath, true);
  if (stage === null || candidate === null) return undefined;
  if (!matchesFileProof(stage, size, checksum) || !matchesFileProof(candidate, size, checksum))
    return undefined;
  if (stage.dev !== candidate.dev || stage.ino !== candidate.ino) return undefined;
  return { dev: candidate.dev, ino: candidate.ino };
}

/** Proves that a temporary manifest name is only another link to its parsed manifest. */
export async function matchingFileIdentity(
  firstPath: string,
  secondPath: string,
): Promise<FileIdentity | undefined> {
  const first = await readFileProof(firstPath, true);
  const second = await readFileProof(secondPath, true);
  if (first === null || second === null) return undefined;
  if (
    first.dev !== second.dev ||
    first.ino !== second.ino ||
    first.size !== second.size ||
    !first.contents.equals(second.contents)
  )
    return undefined;
  return { dev: first.dev, ino: first.ino };
}

export async function restoreOrVerifyFinal(
  stagePath: string,
  projectDirectory: string,
  artifact: ArtifactRow,
  report: MutableRecoveryReport,
): Promise<FileIdentity> {
  const stage = await readFileProof(stagePath);
  if (stage === null) throw missingArtifact(artifact.id);
  assertFileProof(stage, artifact.sizeBytes, artifact.checksumSha256);
  const finalPath = resolve(projectDirectory, artifactFilename(artifact));
  const final = await readFileProof(finalPath, true);
  if (final === null) {
    await link(stagePath, finalPath);
    await syncDirectory(projectDirectory);
    report.finalsRestored += 1;
  } else {
    assertFileProof(final, artifact.sizeBytes, artifact.checksumSha256);
  }
  return { dev: stage.dev, ino: stage.ino };
}

export async function requireEvidence(path: string, artifact: ArtifactRow): Promise<FileIdentity> {
  const proof = await readFileProof(path, true);
  if (proof === null) throw missingArtifact(artifact.id);
  assertFileProof(proof, artifact.sizeBytes, artifact.checksumSha256);
  return { dev: proof.dev, ino: proof.ino };
}

function assertManifestMatchesArtifact(
  manifest: ExportPublicationManifest,
  artifact: ArtifactRow,
): void {
  if (
    manifest.project_id !== artifact.projectId ||
    manifest.artifact_id !== artifact.id ||
    manifest.format !== artifact.format ||
    manifest.relative_path !== artifact.relativePath ||
    manifest.size_bytes !== artifact.sizeBytes ||
    manifest.checksum_sha256 !== artifact.checksumSha256
  ) {
    throw new Error(`Committed export ${artifact.id} does not match its recovery manifest.`);
  }
}

export function assertCanonicalArtifact(artifact: ArtifactRow): void {
  assertCanonicalExportArtifactEvidence(artifact);
}

export function artifactFilename(value: Pick<ArtifactRow, "id" | "format">): string {
  return exportArtifactFilename(value.id, value.format);
}

function manifestFilename(
  value: Pick<ExportPublicationManifest, "artifact_id" | "format">,
): string {
  return exportArtifactFilename(value.artifact_id, value.format);
}

export async function realDirectory(
  path: string,
  root: string,
  missingAllowed: boolean,
): Promise<boolean> {
  let details: Awaited<ReturnType<typeof lstat>>;
  try {
    details = await lstat(path);
  } catch (error) {
    if (missingAllowed && errorCode(error) === "ENOENT") return false;
    throw error;
  }
  if (details.isSymbolicLink() || !details.isDirectory()) {
    throw new Error(`Unsafe export directory: ${path}`);
  }
  const actual = await realpath(path);
  if (!isDescendant(root, actual)) throw new Error(`Export directory escapes its root: ${path}`);
  return true;
}

export async function assertTreeContainsNoSymlinks(directory: string): Promise<void> {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const path = resolve(directory, entry.name);
    if (entry.isSymbolicLink()) {
      throw new Error(`Unsafe symlink in deleted project export tree: ${path}`);
    }
    if (entry.isDirectory()) await assertTreeContainsNoSymlinks(path);
    else if (!entry.isFile())
      throw new Error(`Unsafe entry in deleted project export tree: ${path}`);
  }
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}

function missingArtifact(id: string): Error {
  return new Error(`Committed export artifact ${id} is missing.`);
}
