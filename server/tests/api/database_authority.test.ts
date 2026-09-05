import { existsSync } from "node:fs";
import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";

async function customConfig() {
  const workspace = await mkdtemp(join(tmpdir(), "novel-engine-api-authority-"));
  const databasePath = join(workspace, "data", "author.sqlite3");
  await mkdir(join(workspace, "data"), { recursive: true });
  return {
    config: loadServerConfig({
      envFile: null,
      workingDirectory: workspace,
      env: { APP_ENVIRONMENT: "testing", DB_URL: `sqlite:///${databasePath}` },
    }),
    databasePath,
    legacyPath: join(workspace, "data", "novel-engine.sqlite3"),
  };
}

describe("configured database authority at the API seam", () => {
  it("opens the exact configured basename", async () => {
    const { config, databasePath, legacyPath } = await customConfig();

    const app = await buildApp({ logger: false, config });
    try {
      expect(app.studioDb?.databasePath).toBe(databasePath);
      expect(existsSync(databasePath)).toBe(true);
      expect(existsSync(legacyPath)).toBe(false);
    } finally {
      await app.close();
    }
  });

  it("rejects a legacy default sibling before opening the configured file", async () => {
    const { config, databasePath, legacyPath } = await customConfig();
    await writeFile(legacyPath, "legacy authority");

    await expect(buildApp({ logger: false, config })).rejects.toThrow(
      expect.objectContaining({
        message: expect.stringContaining(databasePath),
      }),
    );
    expect(existsSync(databasePath)).toBe(false);
    expect(existsSync(join(config.dataDirectory, "backups"))).toBe(false);
  });
});
