import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";

const temporaryDirectories: string[] = [];

afterEach(async () => {
  await Promise.all(
    temporaryDirectories.splice(0).map((directory) => rm(directory, { recursive: true })),
  );
});

function load(env: Record<string, string> = {}) {
  return loadServerConfig({ env, envFile: null });
}

describe("workflow capacity configuration", () => {
  it("applies defaults of four per app and two per project", () => {
    const config = load();
    expect(config.maxActiveWorkflows).toBe(4);
    expect(config.maxActiveWorkflowsPerProject).toBe(2);
  });

  it("gives process values precedence over the environment file", async () => {
    const workspace = await mkdtemp(join(tmpdir(), "novel-engine-capacity-config-"));
    temporaryDirectories.push(workspace);
    const envFile = join(workspace, ".env.local");
    await writeFile(
      envFile,
      "API_MAX_ACTIVE_WORKFLOWS=8\nAPI_MAX_ACTIVE_WORKFLOWS_PER_PROJECT=3\n",
    );

    const config = loadServerConfig({
      envFile,
      workingDirectory: workspace,
      env: {
        API_MAX_ACTIVE_WORKFLOWS: "12",
        API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT: "5",
      },
    });

    expect(config.maxActiveWorkflows).toBe(12);
    expect(config.maxActiveWorkflowsPerProject).toBe(5);
  });

  it("rejects out-of-range, non-integer, and inverted limits", () => {
    const cases: readonly [Record<string, string>, string][] = [
      [{ API_MAX_ACTIVE_WORKFLOWS: "0" }, "API_MAX_ACTIVE_WORKFLOWS"],
      [{ API_MAX_ACTIVE_WORKFLOWS: "1025" }, "API_MAX_ACTIVE_WORKFLOWS"],
      [{ API_MAX_ACTIVE_WORKFLOWS: "1.5" }, "API_MAX_ACTIVE_WORKFLOWS"],
      [{ API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT: "0" }, "API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT"],
      [{ API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT: "1025" }, "API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT"],
      [{ API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT: "2.5" }, "API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT"],
      [
        { API_MAX_ACTIVE_WORKFLOWS: "2", API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT: "3" },
        "must not exceed",
      ],
    ];

    for (const [env, expectedMessage] of cases) {
      expect(() => load(env)).toThrow(expectedMessage);
    }
  });

  it("accepts the inclusive boundaries", () => {
    const config = load({
      API_MAX_ACTIVE_WORKFLOWS: "1024",
      API_MAX_ACTIVE_WORKFLOWS_PER_PROJECT: "1",
    });
    expect(config.maxActiveWorkflows).toBe(1024);
    expect(config.maxActiveWorkflowsPerProject).toBe(1);
  });
});
