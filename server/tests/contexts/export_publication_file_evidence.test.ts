import { createHash } from "node:crypto";
import { appendFile, mkdtemp, rename, rm, truncate, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { afterEach, describe, expect, it, vi } from "vitest";

import { EXPORT_CAPACITY_LIMITS } from "../../src/contexts/studio/domain/exceptions.js";
import { readFileProof } from "../../src/contexts/studio/infrastructure/export_publication_file_evidence.js";

const directories: string[] = [];

afterEach(async () => {
  await Promise.all(directories.splice(0).map((directory) => rm(directory, { recursive: true })));
});

async function filePath(name: string): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-file-proof-"));
  directories.push(directory);
  return join(directory, name);
}

describe("bounded export descriptor evidence", () => {
  it("hashes an exact sparse artifact with bounded proof-only chunks", async () => {
    const path = await filePath("sparse.bin");
    const size = EXPORT_CAPACITY_LIMITS.artifact_bytes;
    await writeFile(path, "");
    await truncate(path, size);
    const reads: number[] = [];

    const proof = await readFileProof(path, {
      hooks: { onRead: (requested) => void reads.push(requested) },
    });

    const hash = createHash("sha256");
    const zeros = Buffer.alloc(65_536);
    for (let remaining = size; remaining > 0; remaining -= zeros.length) hash.update(zeros);
    expect(proof).toMatchObject({ size: BigInt(size), checksum: hash.digest("hex") });
    expect(proof).not.toHaveProperty("contents");
    expect(Math.max(...reads)).toBeLessThanOrEqual(65_536);
  });

  it("rejects plus one from descriptor size before allocating or reading", async () => {
    const path = await filePath("oversized.bin");
    await writeFile(path, "");
    await truncate(path, EXPORT_CAPACITY_LIMITS.artifact_bytes + 1);
    const allocate = vi.fn(Buffer.allocUnsafe);
    const onRead = vi.fn();

    await expect(
      readFileProof(path, {
        collectContents: true,
        capacity: {
          resource: "artifact_bytes",
          limit: EXPORT_CAPACITY_LIMITS.artifact_bytes,
        },
        hooks: { allocate, onRead },
      }),
    ).rejects.toMatchObject({
      resource: "artifact_bytes",
      limit: EXPORT_CAPACITY_LIMITS.artifact_bytes,
      observed: EXPORT_CAPACITY_LIMITS.artifact_bytes + 1,
    });
    expect(allocate).not.toHaveBeenCalled();
    expect(onRead).not.toHaveBeenCalled();
  });

  it("collects exactly once after preflight and tolerates positive short reads", async () => {
    const path = await filePath("collected.bin");
    const contents = Buffer.from("short reads still produce the exact body");
    await writeFile(path, contents);
    const allocate = vi.fn(Buffer.allocUnsafe);

    const proof = await readFileProof(path, {
      collectContents: true,
      hooks: { allocate, maxReadBytes: 3 },
    });

    if (proof === null || !("contents" in proof)) throw new Error("expected collected proof");
    expect(proof.contents).toEqual(contents);
    expect(allocate).toHaveBeenCalledTimes(1);
    expect(allocate).toHaveBeenCalledWith(contents.length);
  });

  it.each([
    {
      label: "growth",
      mutate: async (path: string) => appendFile(path, "grown"),
    },
    {
      label: "truncation",
      mutate: async (path: string) => truncate(path, 2),
    },
    {
      label: "final-path replacement",
      mutate: async (path: string) => {
        await rename(path, `${path}.old`);
        await writeFile(path, "replacement");
      },
    },
  ])("rejects descriptor $label after initial stat", async ({ mutate }) => {
    const path = await filePath("raced.bin");
    await writeFile(path, "stable original bytes");

    await expect(
      readFileProof(path, { hooks: { afterInitialStat: () => mutate(path) } }),
    ).rejects.toThrow(/changed|grew|truncated|replaced/i);
  });

  it("rejects a checksum mismatch without retaining file contents", async () => {
    const path = await filePath("checksum.bin");
    await writeFile(path, "actual bytes");

    await expect(
      readFileProof(path, {
        expected: { sizeBytes: 12, checksumSha256: "0".repeat(64) },
      }),
    ).rejects.toThrow(/integrity evidence does not match/i);
  });
});
