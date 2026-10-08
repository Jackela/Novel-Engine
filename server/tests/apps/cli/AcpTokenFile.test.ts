import { chmod, mkdtemp, readFile, rm, stat, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";
import { AcpTokenFile } from "../../../src/shared/infrastructure/acp/AcpTokenFile.js";

it("creates a private gateway token once and reuses it without exposing it", async () => {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-token-"));
  try {
    const path = join(directory, "gateway.token");
    const token = await AcpTokenFile(path, { create: true });
    expect(Buffer.from(token, "base64url")).toHaveLength(32);
    expect((await stat(path)).mode & 0o777).toBe(0o600);
    expect(await AcpTokenFile(path)).toBe(token);
    expect((await readFile(path, "utf8")).trim()).toBe(token);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

it("refuses an exposed token and a symlink without changing either file", async () => {
  const directory = await mkdtemp(join(tmpdir(), "ne-acp-token-refusal-"));
  try {
    const path = join(directory, "token");
    const original = await AcpTokenFile(path, { create: true });
    await chmod(path, 0o644);
    await expect(AcpTokenFile(path, { create: true })).rejects.toThrow("mode 0600");
    expect((await readFile(path, "utf8")).trim()).toBe(original);
    await chmod(path, 0o600);
    const link = join(directory, "link");
    await symlink(path, link);
    await expect(AcpTokenFile(link)).rejects.toThrow();
    await expect(AcpTokenFile(link, { create: true })).rejects.toThrow();
    expect(await AcpTokenFile(path)).toBe(original);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
