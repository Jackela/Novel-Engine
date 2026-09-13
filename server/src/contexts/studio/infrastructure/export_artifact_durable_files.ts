// Durable file primitives shared by the export publication pipeline: confined
// staging directories, fsync-backed artifact/manifest writes, and the
// path-confinement helper every export boundary relies on. Extracted from
// export_artifact_publication_stages.ts so the stages module only keeps its
// step functions; moved verbatim to preserve publication behavior.
import { constants } from "node:fs";
import { link, lstat, mkdir, open, realpath } from "node:fs/promises";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";

import { EXPORT_CAPACITY_LIMITS, ExportCapacityExceededError } from "../domain/exceptions.js";
import {
  cleanupOwnedFile,
  errorCode,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";
import type { ExportPublicationManifest } from "./export_artifact_publication.js";

export function isDescendant(root: string, candidate: string): boolean {
  const offset = relative(root, candidate);
  return offset !== "" && offset !== ".." && !offset.startsWith(`..${sep}`) && !isAbsolute(offset);
}

export async function durableStagingDirectory(projectDirectory: string): Promise<string> {
  const projectDetails = await lstat(projectDirectory);
  if (projectDetails.isSymbolicLink() || !projectDetails.isDirectory()) {
    throw new Error("Export project directory is not a real directory.");
  }
  const realProjectDirectory = await realpath(projectDirectory);
  const candidate = resolve(realProjectDirectory, ".staging");
  if (!isDescendant(realProjectDirectory, candidate)) {
    throw new Error("Export staging directory is outside the project root.");
  }
  let details: Awaited<ReturnType<typeof lstat>>;
  try {
    details = await lstat(candidate);
  } catch (error) {
    if (errorCode(error) !== "ENOENT") throw error;
    try {
      await mkdir(candidate);
    } catch (mkdirError) {
      if (errorCode(mkdirError) !== "EEXIST") throw mkdirError;
    }
    details = await lstat(candidate);
  }
  if (details.isSymbolicLink() || !details.isDirectory()) {
    throw new Error("Export staging path is not a real directory.");
  }
  const actual = await realpath(candidate);
  if (!isDescendant(realProjectDirectory, actual)) {
    throw new Error("Export staging directory escapes the project root.");
  }
  await syncDirectory(realProjectDirectory);
  return actual;
}

export async function writeDurableFile(
  path: string,
  contents: Buffer,
  onCreated?: (identity: FileIdentity) => void,
  afterWrite?: (path: string) => Promise<void>,
): Promise<FileIdentity> {
  const handle = await open(path, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL);
  try {
    const details = await handle.stat({ bigint: true });
    const identity = { dev: details.dev, ino: details.ino };
    onCreated?.(identity);
    await handle.writeFile(contents);
    await afterWrite?.(path);
    const written = await handle.stat();
    if (!written.isFile()) throw new Error("Export stage is not a regular file.");
    assertArtifactDescriptorSize(written.size, contents.length);
    await handle.sync();
    return identity;
  } finally {
    await handle.close();
  }
}

export function assertArtifactDescriptorSize(observed: number, expected: number): void {
  const limit = EXPORT_CAPACITY_LIMITS.artifact_bytes;
  if (observed > limit) {
    throw new ExportCapacityExceededError("artifact_bytes", limit, observed);
  }
  if (observed !== expected) throw new Error("Export stage size changed during publication.");
}

export async function writeDurableManifest(
  temporary: string,
  target: string,
  contents: Buffer,
  onTemporaryCreated: (identity: FileIdentity) => void,
  onManifestLinked: (identity: FileIdentity) => void,
): Promise<FileIdentity> {
  const identity = await writeDurableFile(temporary, contents, onTemporaryCreated);
  await link(temporary, target);
  onManifestLinked(identity);
  await syncDirectory(dirname(target));
  await cleanupOwnedFile(temporary, identity);
  await syncDirectory(dirname(target));
  return identity;
}

export function encodeManifest(manifest: ExportPublicationManifest): Buffer {
  const contents = Buffer.from(`${JSON.stringify(manifest)}\n`, "utf8");
  const limit = EXPORT_CAPACITY_LIMITS.manifest_bytes;
  if (contents.length > limit) {
    throw new ExportCapacityExceededError("manifest_bytes", limit, contents.length);
  }
  return contents;
}

export function safeId(value: string): string {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error("Unsafe export publication id.");
  return value;
}
