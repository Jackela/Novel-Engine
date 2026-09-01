import { randomUUID } from "node:crypto";
import { constants } from "node:fs";
import { link, open, rename, unlink } from "node:fs/promises";
import { dirname } from "node:path";

import {
  cleanupPublicationSidecars,
  errorCode,
  type FileIdentity,
  syncDirectory,
} from "./export_artifact_fs_support.js";

export type OwnedFinalRemoval = "missing" | "removed" | "replacement-restored";

export const REPLACEMENT_PRESERVED_ERROR =
  "Export rollback preserved a replacement and its recovery sidecars for operator review.";

export async function rollbackPublication(
  target: string,
  stage: string,
  manifest: string,
  stagingDirectory: string,
  contents: Buffer,
  dev: bigint,
  ino: bigint,
  manifestIdentity: FileIdentity | undefined,
  afterQuarantine?: (quarantine: string, target: string) => Promise<void>,
): Promise<void> {
  const removal = await removeOwnedFinalViaQuarantine(target, contents, dev, ino, afterQuarantine);
  if (removal === "replacement-restored") throw new Error(REPLACEMENT_PRESERVED_ERROR);
  await cleanupPublicationSidecars(stage, manifest, stagingDirectory, {
    stage: { dev, ino },
    manifest: manifestIdentity,
  });
}

export async function removeOwnedFinalViaQuarantine(
  target: string,
  contents: Buffer,
  dev: bigint,
  ino: bigint,
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
  const owned = await isExpectedFile(quarantine, contents, dev, ino);
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

async function isExpectedFile(
  path: string,
  contents: Buffer,
  dev: bigint,
  ino: bigint,
): Promise<boolean> {
  let handle: Awaited<ReturnType<typeof open>>;
  try {
    handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  } catch (error) {
    if (isMissingOrReplacedTarget(error)) return false;
    throw error;
  }
  try {
    const details = await handle.stat({ bigint: true });
    const actual = await handle.readFile();
    return (
      details.isFile() && details.dev === dev && details.ino === ino && actual.equals(contents)
    );
  } finally {
    await handle.close();
  }
}

function isMissingOrReplacedTarget(error: unknown): boolean {
  const code = errorCode(error);
  return code === "ENOENT" || code === "ELOOP";
}
