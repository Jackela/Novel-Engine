import { createHash } from "node:crypto";
import { type BigIntStats, constants } from "node:fs";
import { type FileHandle, lstat, open } from "node:fs/promises";

import { ExportCapacityExceededError, type ExportCapacityResource } from "../domain/exceptions.js";
import { errorCode } from "./export_artifact_fs_support.js";

const MAX_READ_BYTES = 65_536;
const UNAVAILABLE_FILE_CODES = new Set(["ENOENT", "ENOTDIR", "ELOOP"]);

/** A classified missing, unsafe, replaced, or integrity-invalid export file. */
export class ExportFileEvidenceError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "ExportFileEvidenceError";
  }
}

export interface FileProof {
  readonly size: bigint;
  readonly checksum: string;
  readonly dev: bigint;
  readonly ino: bigint;
}

interface CollectedFileProof extends FileProof {
  readonly contents: Buffer;
}

interface ExpectedFileProof {
  readonly sizeBytes: number;
  readonly checksumSha256: string;
}

interface FileProofCapacity {
  readonly resource: ExportCapacityResource;
  readonly limit: number;
}

/** Internal deterministic seams; production callers must leave these absent. */
interface FileProofTestHooks {
  readonly allocate?: ((size: number) => Buffer) | undefined;
  readonly maxReadBytes?: number | undefined;
  readonly afterInitialStat?: (() => Promise<void>) | undefined;
  readonly onRead?: ((requested: number, actual: number) => void) | undefined;
}

interface ReadFileProofOptions {
  readonly missingAllowed?: boolean | undefined;
  readonly collectContents?: boolean | undefined;
  readonly capacity?: FileProofCapacity | undefined;
  readonly expected?: ExpectedFileProof | undefined;
  readonly hooks?: FileProofTestHooks | undefined;
}

/** BigInt stats of one open descriptor, as returned by `handle.stat`. */
type DescriptorStats = BigIntStats;

/**
 * Proves one no-follow regular-file descriptor in bounded chunks. Proof mode
 * retains only scalar evidence; collection allocates exactly once after the
 * descriptor kind, size, safe-integer, and optional capacity checks pass.
 */
export async function readFileProof(
  path: string,
  options: ReadFileProofOptions = {},
): Promise<FileProof | CollectedFileProof | null> {
  const handle = await openProofHandle(path, options);
  if (handle === null) return null;
  try {
    const initial = await statInitialProofEvidence(handle, options);
    const { contents, checksum } = await readProofChunks(handle, initial, options);
    await assertStableProofDescriptor(path, handle, initial, options);
    const proof: FileProof = { size: initial.size, checksum, dev: initial.dev, ino: initial.ino };
    if (options.expected !== undefined) assertFileProof(proof, options.expected);
    return contents === undefined ? proof : { ...proof, contents };
  } finally {
    await handle.close();
  }
}

// Step 1: open the no-follow descriptor; classify a tolerated missing file as
// `null` and unavailable paths as evidence errors.
async function openProofHandle(
  path: string,
  options: ReadFileProofOptions,
): Promise<FileHandle | null> {
  try {
    return await open(path, constants.O_RDONLY | constants.O_NOFOLLOW);
  } catch (error) {
    if (options.missingAllowed === true && errorCode(error) === "ENOENT") return null;
    if (isUnavailableFileError(error)) {
      throw new ExportFileEvidenceError("Export file is unavailable.", { cause: error });
    }
    throw error;
  }
}

// Step 2: prove the descriptor kind, capacity, safe-integer size, and optional
// expected size before any buffer allocation or byte is read.
async function statInitialProofEvidence(
  handle: FileHandle,
  options: ReadFileProofOptions,
): Promise<DescriptorStats> {
  const initial = await handle.stat({ bigint: true });
  if (!initial.isFile()) throw new ExportFileEvidenceError("Export file is not regular.");
  assertCapacity(initial.size, options.capacity);
  if (initial.size > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error("Export file size exceeds the safe descriptor range.");
  }
  if (options.expected !== undefined && initial.size !== BigInt(options.expected.sizeBytes)) {
    throw new ExportFileEvidenceError("Export artifact integrity evidence does not match.");
  }
  await options.hooks?.afterInitialStat?.();
  return initial;
}

// Step 3: read the full descriptor in bounded chunks into the digest,
// allocating the collection buffer exactly once when contents are requested.
async function readProofChunks(
  handle: FileHandle,
  initial: DescriptorStats,
  options: ReadFileProofOptions,
): Promise<{ readonly contents: Buffer | undefined; readonly checksum: string }> {
  const size = Number(initial.size);
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
    if (bytesRead === 0) {
      throw new ExportFileEvidenceError("Export file was truncated during descriptor read.");
    }
    digest.update(buffer.subarray(bufferOffset, bufferOffset + bytesRead));
    offset += bytesRead;
  }
  return { contents, checksum: digest.digest("hex") };
}

// Step 4: prove nothing grew, changed, or replaced the path behind the
// descriptor between the first stat and the completed read.
async function assertStableProofDescriptor(
  path: string,
  handle: FileHandle,
  initial: DescriptorStats,
  options: ReadFileProofOptions,
): Promise<void> {
  const extra = Buffer.allocUnsafe(1);
  const extraRead = await handle.read(extra, 0, 1, Number(initial.size));
  options.hooks?.onRead?.(1, extraRead.bytesRead);
  if (extraRead.bytesRead !== 0) {
    throw new ExportFileEvidenceError("Export file grew during descriptor read.");
  }
  const after = await handle.stat({ bigint: true });
  if (
    !after.isFile() ||
    after.dev !== initial.dev ||
    after.ino !== initial.ino ||
    after.size !== initial.size ||
    after.ctimeNs !== initial.ctimeNs ||
    after.mtimeNs !== initial.mtimeNs
  ) {
    throw new ExportFileEvidenceError("Export file changed during descriptor read.");
  }
  await assertPathStillOwnsDescriptor(path, initial.dev, initial.ino);
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
    throw new ExportFileEvidenceError("Export artifact integrity evidence does not match.");
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
    if (isUnavailableFileError(error)) {
      throw new ExportFileEvidenceError("Export file path was replaced during descriptor read.", {
        cause: error,
      });
    }
    throw error;
  }
  if (!current.isFile() || current.isSymbolicLink() || current.dev !== dev || current.ino !== ino) {
    throw new ExportFileEvidenceError("Export file path was replaced during descriptor read.");
  }
}

function isUnavailableFileError(error: unknown): boolean {
  const code = errorCode(error);
  return code !== undefined && UNAVAILABLE_FILE_CODES.has(code);
}
