import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { link, open, rename, unlink } from "node:fs/promises";
import { dirname } from "node:path";

export interface FileIdentity {
  readonly dev: bigint;
  readonly ino: bigint;
}

export interface PublicationSidecarOwnership {
  readonly stage?: FileIdentity | undefined;
  readonly manifest?: FileIdentity | undefined;
}

export async function cleanupPublicationSidecars(
  stage: string,
  manifest: string,
  stagingDirectory: string,
  ownership: PublicationSidecarOwnership,
): Promise<void> {
  const failures: unknown[] = [];
  for (const [path, identity] of [
    [stage, ownership.stage],
    [manifest, ownership.manifest],
  ] as const) {
    if (identity === undefined) continue;
    try {
      await cleanupOwnedFile(path, identity);
    } catch (failure) {
      failures.push(failure);
    }
  }
  try {
    await syncDirectory(stagingDirectory);
  } catch (failure) {
    if (errorCode(failure) !== "ENOENT") failures.push(failure);
  }
  if (failures.length === 1) throw failures[0];
  if (failures.length > 1) throw new AggregateError(failures, "Export sidecar cleanup failed.");
}

/** Remove only the captured inode; a replacement is restored or quarantined. */
export async function cleanupOwnedFile(
  path: string,
  expected: FileIdentity | undefined,
): Promise<void> {
  if (expected === undefined) return;
  const quarantined = await quarantineOwnedFile(path, expected);
  if (quarantined === undefined) return;
  await unlink(quarantined.path);
  await syncDirectory(dirname(path));
}

/** Durably isolate only the captured inode behind an unpredictable name. */
export async function quarantineOwnedFile(
  path: string,
  expected: FileIdentity,
): Promise<{ readonly path: string; readonly identity: FileIdentity } | undefined> {
  const quarantine = `${cleanupBasePath(path)}.cleanup-${randomUUID()}`;
  try {
    await rename(path, quarantine);
  } catch (error) {
    if (errorCode(error) === "ENOENT") return undefined;
    throw error;
  }
  await syncDirectory(dirname(path));
  let actual: FileIdentity;
  try {
    actual = await fileIdentity(quarantine);
  } catch (error) {
    return restoreReplacement(quarantine, path, error);
  }
  if (actual.dev !== expected.dev || actual.ino !== expected.ino) {
    return restoreReplacement(
      quarantine,
      path,
      new Error("Export sidecar path was replaced before cleanup."),
    );
  }
  return { path: quarantine, identity: actual };
}

function cleanupBasePath(path: string): string {
  let base = path;
  for (;;) {
    const next = base.replace(/\.cleanup-[A-Za-z0-9_-]+$/, "");
    if (next === base) return base;
    base = next;
  }
}

async function fileIdentity(path: string): Promise<FileIdentity> {
  const handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const details = await handle.stat({ bigint: true });
    if (!details.isFile()) throw new Error(`Export sidecar is not a regular file: ${path}`);
    return { dev: details.dev, ino: details.ino };
  } finally {
    await handle.close();
  }
}

async function restoreReplacement(
  quarantine: string,
  path: string,
  originalError: unknown,
): Promise<never> {
  try {
    await link(quarantine, path);
    await syncDirectory(dirname(path));
    await unlink(quarantine);
    await syncDirectory(dirname(path));
  } catch (restoreError) {
    throw new AggregateError(
      [originalError, restoreError],
      "Export sidecar replacement was quarantined for operator recovery.",
    );
  }
  throw new Error("Export sidecar cleanup preserved a replacement.", { cause: originalError });
}

export async function syncDirectory(path: string): Promise<void> {
  const handle = await open(path, constants.O_RDONLY);
  try {
    await handle.sync();
  } finally {
    await handle.close();
  }
}

export function errorCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null || !("code" in error)) return undefined;
  return typeof error.code === "string" ? error.code : undefined;
}
