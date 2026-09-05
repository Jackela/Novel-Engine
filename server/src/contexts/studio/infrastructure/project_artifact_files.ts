import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { lstat, open, realpath, rename, rm, unlink } from "node:fs/promises";
import { isAbsolute, relative, resolve, sep } from "node:path";

import type { ProjectArtifactCleaner } from "../application/ports/project_artifact_cleaner.js";

const SAFE_PROJECT_ID = /^[A-Za-z0-9_-]+$/;

interface FileIdentity {
  readonly device: bigint;
  readonly inode: bigint;
}

interface FileDetails {
  readonly dev: bigint;
  readonly ino: bigint;
  isDirectory(): boolean;
  isSymbolicLink(): boolean;
}

interface ConfinedExportsRoot {
  readonly identity: FileIdentity;
  readonly path: string;
}

interface ConfinedProjectLeaf {
  readonly identity: FileIdentity;
  readonly kind: "directory" | "symbolic-link";
  readonly path: string;
}

export interface FilesystemProjectArtifactCleanerOptions {
  /** Deterministic failure seam after confinement checks and before removal. */
  readonly beforeRemove?: ((projectDirectory: string) => Promise<void> | void) | undefined;
}

/** Confined, symlink-safe deletion of one project's complete export tree. */
export class FilesystemProjectArtifactCleaner implements ProjectArtifactCleaner {
  constructor(
    private readonly dataDirectory: string,
    private readonly options: FilesystemProjectArtifactCleanerOptions = {},
  ) {}

  async removeProjectArtifacts(projectId: string): Promise<void> {
    assertSafeProjectId(projectId);
    const exportsRoot = await confinedExportsRoot(this.dataDirectory);
    if (exportsRoot === null) return;
    const initialLeaf = await confinedProjectLeaf(exportsRoot.path, projectId);
    if (initialLeaf === null) return;
    await this.options.beforeRemove?.(initialLeaf.path);

    // Re-establish both confinement and inode ownership at the destructive
    // boundary. The parent can otherwise be replaced with a symlink after the
    // first check and make a recursive removal escape the data directory.
    await assertExportsRootUnchanged(this.dataDirectory, exportsRoot);
    const currentLeaf = await confinedProjectLeaf(exportsRoot.path, projectId);
    if (currentLeaf === null) return;
    if (
      currentLeaf.kind !== initialLeaf.kind ||
      !sameIdentity(currentLeaf.identity, initialLeaf.identity)
    ) {
      throw new Error("Project export directory changed during artifact cleanup.");
    }
    const quarantine = resolve(exportsRoot.path, `.${projectId}.deleting-${randomUUID()}`);
    if (!isDescendant(exportsRoot.path, quarantine)) {
      throw new Error("Project artifact quarantine is outside the exports root.");
    }
    if (!(await renameIfPresent(currentLeaf.path, quarantine))) return;

    // A rename gives deletion a private leaf name. Rechecking the parent and
    // the renamed inode makes any detected race fail closed before recursion.
    await assertExportsRootUnchanged(this.dataDirectory, exportsRoot);
    const quarantinedDetails = await leafDetails(quarantine);
    if (
      quarantinedDetails === null ||
      !sameIdentity(identityOf(quarantinedDetails), currentLeaf.identity) ||
      !matchesKind(quarantinedDetails, currentLeaf.kind)
    ) {
      throw new Error("Project export directory changed during artifact cleanup.");
    }
    if (currentLeaf.kind === "symbolic-link") {
      await unlinkIfPresent(quarantine);
    } else {
      await removeDirectoryIfPresent(quarantine);
    }
    await assertExportsRootUnchanged(this.dataDirectory, exportsRoot);
    await syncDirectory(exportsRoot.path);
  }
}

async function confinedExportsRoot(dataDirectory: string): Promise<ConfinedExportsRoot | null> {
  const dataRoot = resolve(dataDirectory);
  const exportsRoot = resolve(dataRoot, "exports");
  if (!isDescendant(dataRoot, exportsRoot)) {
    throw new Error("Exports root is outside the configured data directory.");
  }
  const details = await leafDetails(exportsRoot);
  if (details === null) return null;
  if (details.isSymbolicLink() || !details.isDirectory()) {
    throw new Error("Exports root is not a real directory.");
  }
  const [actualDataRoot, actualExportsRoot] = await Promise.all([
    realpath(dataRoot),
    realpath(exportsRoot),
  ]);
  if (!isDescendant(actualDataRoot, actualExportsRoot)) {
    throw new Error("Exports root escapes the configured data directory.");
  }
  return { identity: identityOf(details), path: actualExportsRoot };
}

async function confinedProjectLeaf(
  exportsRoot: string,
  projectId: string,
): Promise<ConfinedProjectLeaf | null> {
  const projectDirectory = resolve(exportsRoot, projectId);
  if (!isDescendant(exportsRoot, projectDirectory)) {
    throw new Error("Project export directory is outside the exports root.");
  }
  const details = await leafDetails(projectDirectory);
  if (details === null) return null;
  if (details.isSymbolicLink()) {
    return {
      identity: identityOf(details),
      kind: "symbolic-link",
      path: projectDirectory,
    };
  }
  if (!details.isDirectory()) {
    throw new Error("Project export path is not a directory.");
  }
  const actualProjectDirectory = await realpath(projectDirectory);
  if (!isDescendant(exportsRoot, actualProjectDirectory)) {
    throw new Error("Project export directory escapes the exports root.");
  }
  return {
    identity: identityOf(details),
    kind: "directory",
    path: projectDirectory,
  };
}

async function assertExportsRootUnchanged(
  dataDirectory: string,
  expected: ConfinedExportsRoot,
): Promise<void> {
  const current = await confinedExportsRoot(dataDirectory);
  if (
    current === null ||
    current.path !== expected.path ||
    !sameIdentity(current.identity, expected.identity)
  ) {
    throw new Error("Exports root changed during project artifact cleanup.");
  }
}

async function leafDetails(path: string): Promise<FileDetails | null> {
  try {
    return await lstat(path, { bigint: true });
  } catch (error) {
    if (errorCode(error) === "ENOENT") return null;
    throw error;
  }
}

async function renameIfPresent(source: string, destination: string): Promise<boolean> {
  try {
    await rename(source, destination);
    return true;
  } catch (error) {
    if (errorCode(error) === "ENOENT") return false;
    throw error;
  }
}

async function unlinkIfPresent(path: string): Promise<boolean> {
  try {
    await unlink(path);
    return true;
  } catch (error) {
    if (errorCode(error) === "ENOENT") return false;
    throw error;
  }
}

async function removeDirectoryIfPresent(path: string): Promise<boolean> {
  try {
    await rm(path, { recursive: true });
    return true;
  } catch (error) {
    if (errorCode(error) === "ENOENT") return false;
    throw error;
  }
}

async function syncDirectory(directory: string): Promise<void> {
  const handle = await open(directory, constants.O_RDONLY);
  try {
    await handle.sync();
  } finally {
    await handle.close();
  }
}

function assertSafeProjectId(projectId: string): void {
  if (!SAFE_PROJECT_ID.test(projectId)) throw new Error("Project id is invalid.");
}

function identityOf(details: FileDetails): FileIdentity {
  return { device: details.dev, inode: details.ino };
}

function sameIdentity(left: FileIdentity, right: FileIdentity): boolean {
  return left.device === right.device && left.inode === right.inode;
}

function matchesKind(details: FileDetails, kind: ConfinedProjectLeaf["kind"]): boolean {
  return kind === "symbolic-link" ? details.isSymbolicLink() : details.isDirectory();
}

function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}

function errorCode(error: unknown): string | undefined {
  return error !== null && typeof error === "object" && "code" in error
    ? String((error as { code?: unknown }).code)
    : undefined;
}
