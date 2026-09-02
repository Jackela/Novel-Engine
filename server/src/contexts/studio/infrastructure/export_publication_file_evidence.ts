import { createHash } from "node:crypto";
import { constants } from "node:fs";
import { lstat, open } from "node:fs/promises";

import { ExportCapacityExceededError, type ExportCapacityResource } from "../domain/exceptions.js";
import { errorCode } from "./export_artifact_fs_support.js";

const MAX_READ_BYTES = 65_536;

export interface FileProof {
  readonly size: bigint;
  readonly checksum: string;
  readonly dev: bigint;
  readonly ino: bigint;
}

export interface CollectedFileProof extends FileProof {
  readonly contents: Buffer;
}

export interface ExpectedFileProof {
  readonly sizeBytes: number;
  readonly checksumSha256: string;
}

export interface FileProofCapacity {
  readonly resource: ExportCapacityResource;
  readonly limit: number;
}

/** Internal deterministic seams; production callers must leave these absent. */
export interface FileProofTestHooks {
  readonly allocate?: ((size: number) => Buffer) | undefined;
  readonly maxReadBytes?: number | undefined;
  readonly afterInitialStat?: (() => Promise<void>) | undefined;
  readonly onRead?: ((requested: number, actual: number) => void) | undefined;
}

export interface ReadFileProofOptions {
  readonly missingAllowed?: boolean | undefined;
  readonly collectContents?: boolean | undefined;
  readonly capacity?: FileProofCapacity | undefined;
  readonly expected?: ExpectedFileProof | undefined;
  readonly hooks?: FileProofTestHooks | undefined;
}

/**
 * Proves one no-follow regular-file descriptor in bounded chunks. Proof mode
 * retains only scalar evidence; collection allocates exactly once after the
 * descriptor kind, size, safe-integer, and optional capacity checks pass.
 */
export async function readFileProof(
  path: string,
  options: ReadFileProofOptions = {},
): Promise<FileProof | CollectedFileProof | null> {
  let handle: Awaited<ReturnType<typeof open>>;
  try {
    handle = await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  } catch (error) {
    if (options.missingAllowed === true && errorCode(error) === "ENOENT") return null;
    throw new Error(`Unsafe or missing export file: ${path}`, { cause: error });
  }
  try {
    const initial = await handle.stat({ bigint: true });
    if (!initial.isFile()) throw new Error(`Export path is not a regular file: ${path}`);
    assertCapacity(initial.size, options.capacity);
    if (initial.size > BigInt(Number.MAX_SAFE_INTEGER)) {
      throw new Error("Export file size exceeds the safe descriptor range.");
    }
    const size = Number(initial.size);
    if (options.expected !== undefined && initial.size !== BigInt(options.expected.sizeBytes)) {
      throw new Error("Export artifact integrity evidence does not match.");
    }
    await options.hooks?.afterInitialStat?.();

    const collect = options.collectContents === true;
    const allocate = options.hooks?.allocate ?? Buffer.allocUnsafe;
    const contents = collect ? allocate(size) : undefined;
    const configuredReadBytes = options.hooks?.maxReadBytes ?? MAX_READ_BYTES;
    const maxReadBytes = Math.max(1, Math.min(MAX_READ_BYTES, configuredReadBytes));
    const scratch = collect
      ? undefined
      : Buffer.allocUnsafe(Math.min(maxReadBytes, Math.max(1, size)));
    const digest = createHash("sha256");
    let offset = 0;
    while (offset < size) {
      const requested = Math.min(maxReadBytes, size - offset);
      const buffer = contents ?? scratch;
      if (buffer === undefined) throw new Error("Export proof read buffer is unavailable.");
      const bufferOffset = contents === undefined ? 0 : offset;
      const { bytesRead } = await handle.read(buffer, bufferOffset, requested, offset);
      options.hooks?.onRead?.(requested, bytesRead);
      if (bytesRead === 0) throw new Error("Export file was truncated during descriptor read.");
      digest.update(buffer.subarray(bufferOffset, bufferOffset + bytesRead));
      offset += bytesRead;
    }

    const extra = Buffer.allocUnsafe(1);
    const extraRead = await handle.read(extra, 0, 1, size);
    options.hooks?.onRead?.(1, extraRead.bytesRead);
    if (extraRead.bytesRead !== 0) throw new Error("Export file grew during descriptor read.");
    const after = await handle.stat({ bigint: true });
    if (
      !after.isFile() ||
      after.dev !== initial.dev ||
      after.ino !== initial.ino ||
      after.size !== initial.size ||
      after.ctimeNs !== initial.ctimeNs ||
      after.mtimeNs !== initial.mtimeNs
    ) {
      throw new Error("Export file changed during descriptor read.");
    }
    await assertPathStillOwnsDescriptor(path, initial.dev, initial.ino);

    const proof: FileProof = {
      size: initial.size,
      checksum: digest.digest("hex"),
      dev: initial.dev,
      ino: initial.ino,
    };
    if (options.expected !== undefined) assertFileProof(proof, options.expected);
    return contents === undefined ? proof : { ...proof, contents };
  } finally {
    await handle.close();
  }
}

export function assertFileProof(
  proof: FileProof,
  expected: ExpectedFileProof | number,
  checksum?: string,
): void {
  const value =
    typeof expected === "number"
      ? { sizeBytes: expected, checksumSha256: checksum ?? "" }
      : expected;
  if (!matchesFileProof(proof, value.sizeBytes, value.checksumSha256)) {
    throw new Error("Export artifact integrity evidence does not match.");
  }
}

export function matchesFileProof(proof: FileProof, size: number, checksum: string): boolean {
  return proof.size === BigInt(size) && proof.checksum === checksum;
}

function assertCapacity(size: bigint, capacity: FileProofCapacity | undefined): void {
  if (capacity === undefined || size <= BigInt(capacity.limit)) return;
  throw new ExportCapacityExceededError(capacity.resource, capacity.limit, capacity.limit + 1);
}

async function assertPathStillOwnsDescriptor(
  path: string,
  dev: bigint,
  ino: bigint,
): Promise<void> {
  let current: Awaited<ReturnType<typeof lstat>>;
  try {
    current = await lstat(path, { bigint: true });
  } catch (error) {
    throw new Error("Export file path was replaced during descriptor read.", { cause: error });
  }
  if (!current.isFile() || current.isSymbolicLink() || current.dev !== dev || current.ino !== ino) {
    throw new Error("Export file path was replaced during descriptor read.");
  }
}
