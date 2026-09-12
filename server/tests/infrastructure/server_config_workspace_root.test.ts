import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  loadServerConfig,
  type ServerConfig,
} from "../../src/shared/infrastructure/config/server_config.js";

/**
 * The workspace-root harness redirects only the root locator: everything else
 * (file reading, defaults, precedence) runs for real. Vitest executes with
 * cwd = server/, so these tests reproduce the README flow of launching from a
 * subdirectory while the checkout root holds `.env.local`.
 */
const workspaceRootHarness = vi.hoisted(() => ({
  workspaceRoot: undefined as string | undefined,
  // Stashed by the module mock factory so tests can assert on locator calls.
  locateWorkspaceRoot: undefined as unknown as ReturnType<typeof vi.fn>,
}));

vi.mock("../../src/shared/infrastructure/workspace_manifest.js", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../src/shared/infrastructure/workspace_manifest.js")>();
  workspaceRootHarness.locateWorkspaceRoot = vi.fn(() => {
    if (workspaceRootHarness.workspaceRoot === undefined) {
      return actual.locateWorkspaceRoot();
    }
    return workspaceRootHarness.workspaceRoot;
  });
  return {
    ...actual,
    locateWorkspaceRoot: workspaceRootHarness.locateWorkspaceRoot,
  };
});

afterEach(() => {
  workspaceRootHarness.workspaceRoot = undefined;
  workspaceRootHarness.locateWorkspaceRoot.mockClear();
});

async function makeWorkspace(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-workspace-root-"));
}

describe("workspace-root-anchored configuration defaults", () => {
  it("reads the workspace-root .env.local when launched from a subdirectory", async () => {
    const workspaceRoot = await makeWorkspace();
    workspaceRootHarness.workspaceRoot = workspaceRoot;
    await writeFile(join(workspaceRoot, ".env.local"), "API_PORT=8123\n");

    const config: ServerConfig = loadServerConfig({ env: {} });

    expect(config.port).toBe(8123);
  });

  it("resolves default relative database paths under the workspace root", async () => {
    const workspaceRoot = await makeWorkspace();
    workspaceRootHarness.workspaceRoot = workspaceRoot;

    const config: ServerConfig = loadServerConfig({ env: {}, envFile: null });

    expect(config.databaseUrl).toBe("sqlite:///./data/novel-engine.sqlite3");
    expect(config.databasePath).toBe(join(workspaceRoot, "data", "novel-engine.sqlite3"));
    expect(config.dataDirectory).toBe(join(workspaceRoot, "data"));
  });

  it("keeps a missing workspace-root .env.local optional", async () => {
    const workspaceRoot = await makeWorkspace();
    workspaceRootHarness.workspaceRoot = workspaceRoot;

    const config: ServerConfig = loadServerConfig({ env: {} });

    expect(config.port).toBe(8000);
    expect(config.databasePath).toBe(join(workspaceRoot, "data", "novel-engine.sqlite3"));
  });

  it("lets explicit inputs override the workspace-root defaults entirely", async () => {
    const workspaceRoot = await makeWorkspace();
    workspaceRootHarness.workspaceRoot = workspaceRoot;
    await writeFile(join(workspaceRoot, ".env.local"), "API_PORT=8123\n");

    const explicitWorkspace = await makeWorkspace();
    const config: ServerConfig = loadServerConfig({
      env: {},
      envFile: join(explicitWorkspace, "explicit.env.local"),
      workingDirectory: explicitWorkspace,
    });

    expect(config.port).toBe(8000);
    expect(config.databasePath).toBe(join(explicitWorkspace, "data", "novel-engine.sqlite3"));
    // Fully-explicit inputs must not touch the workspace-root locator at all.
    expect(workspaceRootHarness.locateWorkspaceRoot).not.toHaveBeenCalled();
  });
});
