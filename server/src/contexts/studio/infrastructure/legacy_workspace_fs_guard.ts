import { type BigIntStats, constants, type Dir } from "node:fs";
import { type FileHandle, lstat, open, opendir, realpath } from "node:fs/promises";
import { dirname, join } from "node:path";

import { InvalidOperationError } from "../../../shared/domain/exceptions.js";
import { LEGACY_IMPORT_LIMITS } from "../application/ports/legacy_workspace_reader.js";
import { ImportCapacityExceededError, type ImportCapacityResource } from "../domain/exceptions.js";

const CHANGED_ERROR = "Legacy workspace changed during inspection.";
const SYMLINK_ERROR = "Legacy workspace must not contain symbolic links.";
const CHAPTER_ERROR = "Legacy workspace chapters must be regular files.";
const READ_CHUNK_BYTES = 64 * 1024;

export interface DirectoryIdentity {
  readonly path: string;
  readonly dev: bigint;
  readonly ino: bigint;
}

export interface ByteBudget {
  total: number;
}

export async function captureDirectory(
  path: string,
  failure: (missing: boolean) => Error,
): Promise<DirectoryIdentity> {
  const stat = await lstatOrNull(path);
  if (stat === null || stat.isSymbolicLink() || !stat.isDirectory()) {
    throw failure(stat === null);
  }
  let canonical: string;
  try {
    canonical = await realpath(path);
  } catch (error) {
    if (isPathShapeError(error)) throw failure(isErrno(error, "ENOENT"));
    throw error;
  }
  const canonicalStat = await lstatOrNull(canonical);
  if (canonicalStat === null || !sameIdentity(stat, canonicalStat)) throw failure(false);
  return { path: canonical, dev: stat.dev, ino: stat.ino };
}

export async function captureOptionalDirectory(
  parent: DirectoryIdentity,
  name: string,
): Promise<DirectoryIdentity | null> {
  const path = join(parent.path, name);
  const stat = await lstatOrNull(path);
  if (stat === null) return null;
  if (stat.isSymbolicLink()) throw new InvalidOperationError(SYMLINK_ERROR);
  if (!stat.isDirectory()) throw new InvalidOperationError(CHAPTER_ERROR);
  const canonical = await realpathOrChanged(path);
  if (dirname(canonical) !== parent.path) throw new InvalidOperationError(CHANGED_ERROR);
  return { path: canonical, dev: stat.dev, ino: stat.ino };
}

export async function readBoundedFile(
  parent: DirectoryIdentity,
  name: string,
  resource: "story_bytes" | "chapter_bytes",
  invalidMessage: string,
  budget: ByteBudget,
  afterOpen?: (path: string) => void | Promise<void>,
): Promise<Buffer> {
  const path = join(parent.path, name);
  const handle = await openNoFollow(
    path,
    invalidMessage,
    resource === "story_bytes" ? invalidMessage : SYMLINK_ERROR,
  );
  try {
    const initial = await handle.stat({ bigint: true });
    if (!initial.isFile()) throw new InvalidOperationError(invalidMessage);
    const limit =
      resource === "story_bytes"
        ? LEGACY_IMPORT_LIMITS.storyBytes
        : LEGACY_IMPORT_LIMITS.chapterBytes;
    assertFileCapacity(resource, limit, initial.size);
    const size = Number(initial.size);
    assertCapacity("workspace_bytes", LEGACY_IMPORT_LIMITS.workspaceBytes, budget.total + size);
    await afterOpen?.(path);
    await assertOpenPathIdentity(handle, path, parent, initial, CHANGED_ERROR);
    const contents = await readFixedBytes(handle, size, resource, limit, budget);
    await assertOpenPathIdentity(handle, path, parent, initial, CHANGED_ERROR);
    return contents;
  } finally {
    await handle.close();
  }
}

async function readFixedBytes(
  handle: FileHandle,
  size: number,
  resource: "story_bytes" | "chapter_bytes",
  limit: number,
  budget: ByteBudget,
): Promise<Buffer> {
  const chunks: Buffer[] = [];
  let offset = 0;
  while (offset < size) {
    const chunk = Buffer.allocUnsafe(Math.min(READ_CHUNK_BYTES, size - offset));
    const { bytesRead } = await handle.read(chunk, 0, chunk.length, offset);
    if (bytesRead === 0) throw new InvalidOperationError(CHANGED_ERROR);
    offset += bytesRead;
    budget.total += bytesRead;
    assertCapacity(resource, limit, offset);
    assertCapacity("workspace_bytes", LEGACY_IMPORT_LIMITS.workspaceBytes, budget.total);
    chunks.push(chunk.subarray(0, bytesRead));
  }
  const extra = Buffer.allocUnsafe(1);
  if ((await handle.read(extra, 0, 1, offset)).bytesRead !== 0) {
    assertCapacity(resource, limit, offset + 1);
    assertCapacity("workspace_bytes", LEGACY_IMPORT_LIMITS.workspaceBytes, budget.total + 1);
    throw new InvalidOperationError(CHANGED_ERROR);
  }
  return Buffer.concat(chunks, offset);
}

async function assertOpenPathIdentity(
  handle: FileHandle,
  path: string,
  parent: DirectoryIdentity,
  initial: BigIntStats,
  message: string,
): Promise<void> {
  const current = await handle.stat({ bigint: true });
  const pathStat = await lstatOrNull(path);
  if (
    !current.isFile() ||
    current.size !== initial.size ||
    !sameIdentity(current, initial) ||
    pathStat === null ||
    pathStat.isSymbolicLink() ||
    !pathStat.isFile() ||
    !sameIdentity(pathStat, current) ||
    (await realpathOrChanged(dirname(path))) !== parent.path ||
    dirname(await realpathOrChanged(path)) !== parent.path
  ) {
    throw new InvalidOperationError(message);
  }
}

export async function assertDirectoryState(identity: DirectoryIdentity): Promise<void> {
  const stat = await lstatOrNull(identity.path);
  if (
    stat === null ||
    stat.isSymbolicLink() ||
    !stat.isDirectory() ||
    stat.dev !== identity.dev ||
    stat.ino !== identity.ino ||
    (await realpathOrChanged(identity.path)) !== identity.path
  ) {
    throw new InvalidOperationError(CHANGED_ERROR);
  }
}

export async function assertOptionalDirectoryState(
  parent: DirectoryIdentity,
  name: string,
  captured: DirectoryIdentity | null,
): Promise<void> {
  if (captured !== null) return assertDirectoryState(captured);
  if ((await lstatOrNull(join(parent.path, name))) !== null) {
    throw new InvalidOperationError(CHANGED_ERROR);
  }
}

export async function openCapturedDirectory(identity: DirectoryIdentity): Promise<Dir> {
  await assertDirectoryState(identity);
  try {
    return await opendir(identity.path);
  } catch (error) {
    if (isPathShapeError(error)) throw new InvalidOperationError(CHANGED_ERROR);
    throw error;
  }
}

export function assertCapacity(
  resource: ImportCapacityResource,
  limit: number,
  observed: number,
): void {
  if (observed > limit) {
    throw new ImportCapacityExceededError(resource, limit, Math.min(observed, limit + 1));
  }
}

function assertFileCapacity(
  resource: "story_bytes" | "chapter_bytes",
  limit: number,
  observed: bigint,
): void {
  if (observed > BigInt(limit)) {
    throw new ImportCapacityExceededError(resource, limit, limit + 1);
  }
}

async function openNoFollow(
  path: string,
  message: string,
  symbolicLinkMessage: string,
): Promise<FileHandle> {
  try {
    return await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  } catch (error) {
    if (isErrno(error, "ELOOP")) throw new InvalidOperationError(symbolicLinkMessage);
    if (isErrno(error, "ENOENT") || isErrno(error, "ENOTDIR")) {
      throw new InvalidOperationError(message);
    }
    throw error;
  }
}

async function lstatOrNull(path: string): Promise<BigIntStats | null> {
  try {
    return await lstat(path, { bigint: true });
  } catch (error) {
    if (isPathShapeError(error)) return null;
    throw error;
  }
}

function sameIdentity(left: BigIntStats, right: BigIntStats): boolean {
  return left.dev === right.dev && left.ino === right.ino;
}

function isErrno(error: unknown, code: string): error is NodeJS.ErrnoException {
  return typeof error === "object" && error !== null && "code" in error && error.code === code;
}

function isPathShapeError(error: unknown): boolean {
  return isErrno(error, "ENOENT") || isErrno(error, "ELOOP") || isErrno(error, "ENOTDIR");
}

async function realpathOrChanged(path: string): Promise<string> {
  try {
    return await realpath(path);
  } catch (error) {
    if (isPathShapeError(error)) throw new InvalidOperationError(CHANGED_ERROR);
    throw error;
  }
}
