import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it, vi } from "vitest";
import { runCli } from "../../../src/apps/cli/main.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";

async function lifecycleHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-cli-lifecycle-"));
  const dataDirectory = join(directory, "data");
  await mkdir(dataDirectory, { recursive: true });
  const databasePath = join(dataDirectory, "novel-engine.sqlite3");
  const lines: string[] = [];
  const context: Parameters<typeof runCli>[1] = {
    envFile: null,
    workingDirectory: directory,
    env: { DB_URL: `sqlite:///${databasePath}`, APP_ENVIRONMENT: "testing" },
    writeLine: (line) => lines.push(line),
  };
  const studio = await openStudioDatabase(databasePath);
  studio.close();
  return { context, databasePath, lines };
}

describe("CLI serve lifecycle", () => {
  it("releases data-directory ownership when the listener fails", async () => {
    const harness = await lifecycleHarness();
    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      serve: {
        owner: "cli-owned",
        run: async () => {
          throw new Error("simulated listen failure");
        },
      },
    });

    expect(code).toBe(1);
    expect(harness.lines.join("\n")).toContain("simulated listen failure");
    const reopened = await openStudioDatabase(harness.databasePath);
    reopened.close();
  });

  it("reports both listener and cleanup failures without losing either cause", async () => {
    const harness = await lifecycleHarness();
    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      serve: {
        owner: "cli-owned",
        run: async (app) => {
          const close = app.close.bind(app);
          Object.defineProperty(app, "close", {
            configurable: true,
            value: async () => {
              await close();
              throw new Error("simulated cleanup failure");
            },
          });
          throw new Error("simulated listen failure");
        },
      },
    });

    expect(code).toBe(1);
    expect(harness.lines).toEqual([
      "Server listen and cleanup both failed.",
      "simulated listen failure",
      "simulated cleanup failure",
    ]);
    const reopened = await openStudioDatabase(harness.databasePath);
    reopened.close();
  });

  it.each([
    { outcome: "fulfillment", runnerFailure: undefined },
    { outcome: "rejection", runnerFailure: new Error("simulated runner-owned failure") },
  ])("leaves a runner-owned $outcome entirely to that runner", async ({ runnerFailure }) => {
    const harness = await lifecycleHarness();
    const addSignal = vi.fn();
    const removeSignal = vi.fn();
    let closeCalls = 0;

    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      shutdownSignalSource: { add: addSignal, remove: removeSignal },
      serve: {
        owner: "runner-owned",
        run: async (app) => {
          const close = app.close.bind(app);
          Object.defineProperty(app, "close", {
            configurable: true,
            value: async () => {
              closeCalls += 1;
              await close();
            },
          });
          await app.close();
          if (runnerFailure !== undefined) throw runnerFailure;
        },
      },
    });

    expect(code).toBe(runnerFailure === undefined ? 0 : 1);
    expect(closeCalls).toBe(1);
    expect(addSignal).not.toHaveBeenCalled();
    expect(removeSignal).not.toHaveBeenCalled();
    expect(harness.lines).toEqual(runnerFailure === undefined ? [] : [runnerFailure.message]);
  });
});

describe("CLI backup lifecycle", () => {
  it("reports both backup and ownership cleanup failures without losing either cause", async () => {
    const harness = await lifecycleHarness();
    const code = await runCli(["backup"], {
      ...harness.context,
      backupDatabaseFile: async () => {
        throw new Error("simulated backup failure");
      },
      acquireDataDirectoryLock: () => ({
        close: () => {
          throw new Error("simulated ownership cleanup failure");
        },
      }),
    });

    expect(code).toBe(1);
    expect(harness.lines).toEqual([
      "Database backup and ownership cleanup both failed.",
      "simulated backup failure",
      "simulated ownership cleanup failure",
    ]);
  });
});
