import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { validateAcpWorkspace } from "../../src/apps/api/validateAcpWorkspace.js";

describe("local ACP runtime profile", () => {
  it("refuses either direction of overlap with Studio data and refuses Grok sandbox downgrades", async () => {
    const root = await mkdtemp(join(tmpdir(), "novel-engine-acp-profile-"));
    const data = join(root, "data");
    const materials = join(root, "materials");
    await mkdir(data);
    await mkdir(materials);
    const profile = {
      proxyUrl: "ws://127.0.0.1/acp",
      tokenFile: undefined,
      command: "grok",
      args: ["--sandbox", "novel-engine", "agent", "stdio"],
      workspaceRoot: materials,
      model: undefined,
    };
    try {
      expect(() => validateAcpWorkspace(profile, data)).not.toThrow();
      for (const workspaceRoot of [root, data])
        expect(() => validateAcpWorkspace({ ...profile, workspaceRoot }, data)).toThrow(
          "must not overlap",
        );
      for (const args of [
        ["agent", "stdio"],
        ["--sandbox", "strict", "agent", "stdio"],
        ["--sandbox", "workspace", "agent", "stdio"],
        ["--sandbox", "strict", "--sandbox", "off"],
        ["--sandbox=off"],
      ])
        expect(() => validateAcpWorkspace({ ...profile, args }, data)).toThrow("custom");
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
});
