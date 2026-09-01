import { createHash } from "node:crypto";
import { constants } from "node:fs";
import { open } from "node:fs/promises";

import { errorCode } from "./export_artifact_fs_support.js";

export interface FileProof {
  readonly contents: Buffer;
  readonly size: bigint;
  readonly checksum: string;
  readonly dev: bigint;
  readonly ino: bigint;
}

export async function readFileProof(
  path: string,
  missingAllowed = false,
): Promise<FileProof | null> {
  let handle: Awaited<ReturnType<typeof open>>;
  try {
    handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  } catch (error) {
    if (missingAllowed && errorCode(error) === "ENOENT") return null;
    throw new Error(`Unsafe or missing export file: ${path}`, { cause: error });
  }
  try {
    const details = await handle.stat({ bigint: true });
    if (!details.isFile()) throw new Error(`Export path is not a regular file: ${path}`);
    const contents = await handle.readFile();
    return {
      contents,
      size: details.size,
      checksum: createHash("sha256").update(contents).digest("hex"),
      dev: details.dev,
      ino: details.ino,
    };
  } finally {
    await handle.close();
  }
}

export function assertFileProof(proof: FileProof, size: number, checksum: string): void {
  if (!matchesFileProof(proof, size, checksum)) {
    throw new Error("Export artifact integrity evidence does not match.");
  }
}

export function matchesFileProof(proof: FileProof, size: number, checksum: string): boolean {
  return (
    proof.size === BigInt(size) && proof.contents.length === size && proof.checksum === checksum
  );
}
