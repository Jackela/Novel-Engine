import { mkdir, mkdtemp } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import type { FastifyInstance } from "fastify";
import { describe, expect, it, vi } from "vitest";

import { buildApp } from "../../../src/apps/api/app.js";
import { runCli, type ServeRunner } from "../../../src/apps/cli/main.js";
import { openStudioDatabase } from "../../../src/shared/infrastructure/db/startup.js";
import { FakeShutdownSignalSource } from "./shutdown_signal_fixtures.js";

async function shutdownHarness() {
  const directory = await mkdtemp(join(tmpdir(), "novel-engine-cli-shutdown-"));
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

function replaceClose(
  app: FastifyInstance,
  replacement: (original: () => Promise<void>) => Promise<void>,
): void {
  const original = app.close.bind(app);
  Object.defineProperty(app, "close", {
    configurable: true,
    value: () => replacement(original),
  });
}

describe("CLI-owned serve shutdown", () => {
  it.each([
    { signal: "SIGINT", expectedCode: 130 },
    { signal: "SIGTERM", expectedCode: 143 },
  ] as const)(
    "closes exactly once and returns $expectedCode for $signal",
    async ({ signal, expectedCode }) => {
      const harness = await shutdownHarness();
      const source = new FakeShutdownSignalSource();
      let closeCalls = 0;
      const serve: ServeRunner = {
        owner: "cli-owned",
        run: async (app) => {
          source.events.push("listen");
          replaceClose(app, async (original) => {
            closeCalls += 1;
            await original();
          });
          source.emit(signal);
          source.emit(signal === "SIGINT" ? "SIGTERM" : "SIGINT");
        },
      };

      const code = await runCli(["serve", "--port", "8765"], {
        ...harness.context,
        serve,
        shutdownSignalSource: source,
      });

      expect(code).toBe(expectedCode);
      expect(closeCalls).toBe(1);
      expect(source.events.slice(0, 3)).toEqual(["add:SIGINT", "add:SIGTERM", "listen"]);
      expect(source.listenerCount("SIGINT")).toBe(0);
      expect(source.listenerCount("SIGTERM")).toBe(0);
      expect(source.removed).toEqual(source.added);
      const reopened = await openStudioDatabase(harness.databasePath);
      reopened.close();
    },
  );

  it("captures a shutdown signal that arrives while listener startup is still settling", async () => {
    const harness = await shutdownHarness();
    const source = new FakeShutdownSignalSource();
    let releaseStartup: (() => void) | undefined;
    const startup = new Promise<void>((resolve) => {
      releaseStartup = resolve;
    });
    const serve: ServeRunner = {
      owner: "cli-owned",
      run: async () => {
        source.emit("SIGTERM");
        releaseStartup?.();
        await startup;
      },
    };

    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      serve,
      shutdownSignalSource: source,
    });

    expect(code).toBe(143);
    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
  });

  it("keeps later signals latched while the one application close is in progress", async () => {
    const harness = await shutdownHarness();
    const source = new FakeShutdownSignalSource();
    let closeCalls = 0;
    let announceClose: (() => void) | undefined;
    let releaseClose: (() => void) | undefined;
    const closeStarted = new Promise<void>((resolve) => {
      announceClose = resolve;
    });
    const closeGate = new Promise<void>((resolve) => {
      releaseClose = resolve;
    });

    const pending = runCli(["serve", "--port", "8765"], {
      ...harness.context,
      shutdownSignalSource: source,
      serve: {
        owner: "cli-owned",
        run: async (app) => {
          replaceClose(app, async (original) => {
            closeCalls += 1;
            announceClose?.();
            await closeGate;
            await original();
          });
          source.emit("SIGINT");
        },
      },
    });

    let code: number | undefined;
    try {
      await closeStarted;
      source.emit("SIGTERM");
      source.emit("SIGINT");
      expect(closeCalls).toBe(1);
      expect(source.listenerCount("SIGINT")).toBe(1);
      expect(source.listenerCount("SIGTERM")).toBe(1);
    } finally {
      releaseClose?.();
      code = await pending;
    }

    expect(code).toBe(130);
    expect(closeCalls).toBe(1);
    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
  });

  it("keeps handlers during delayed cleanup after listener startup fails", async () => {
    const harness = await shutdownHarness();
    const source = new FakeShutdownSignalSource();
    const listenFailure = new Error("simulated listen failure");
    let closeCalls = 0;
    let announceClose: (() => void) | undefined;
    let releaseClose: (() => void) | undefined;
    const closeStarted = new Promise<void>((resolve) => {
      announceClose = resolve;
    });
    const closeGate = new Promise<void>((resolve) => {
      releaseClose = resolve;
    });

    const pending = runCli(["serve", "--port", "8765"], {
      ...harness.context,
      shutdownSignalSource: source,
      serve: {
        owner: "cli-owned",
        run: async (app) => {
          replaceClose(app, async (original) => {
            closeCalls += 1;
            announceClose?.();
            await closeGate;
            await original();
          });
          throw listenFailure;
        },
      },
    });

    let code: number | undefined;
    try {
      await closeStarted;
      expect(closeCalls).toBe(1);
      expect(source.listenerCount("SIGINT")).toBe(1);
      expect(source.listenerCount("SIGTERM")).toBe(1);
      source.emit("SIGINT");
      source.emit("SIGTERM");
      expect(closeCalls).toBe(1);
    } finally {
      releaseClose?.();
      code = await pending;
    }

    expect(code).toBe(1);
    expect(closeCalls).toBe(1);
    expect(harness.lines).toEqual([listenFailure.message]);
    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
    expect(source.removed).toEqual(source.added);
  });

  it("closes the built app and never calls the runner when signal registration fails", async () => {
    const harness = await shutdownHarness();
    const registrationFailure = new Error("simulated signal registration failure");
    const source = new FakeShutdownSignalSource(registrationFailure);
    const run = vi.fn(async () => undefined);

    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      serve: { owner: "cli-owned", run },
      shutdownSignalSource: source,
    });

    expect(code).toBe(1);
    expect(run).not.toHaveBeenCalled();
    expect(harness.lines).toEqual([registrationFailure.message]);
    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
    const reopened = await openStudioDatabase(harness.databasePath);
    reopened.close();
  });

  it("preserves registration then application cleanup failures in that order", async () => {
    const harness = await shutdownHarness();
    const registrationFailure = new Error("simulated signal registration failure");
    const cleanupFailure = new Error("simulated registration cleanup failure");
    const source = new FakeShutdownSignalSource(registrationFailure);

    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      serve: { owner: "cli-owned", run: async () => undefined },
      shutdownSignalSource: source,
      buildApplication: async (options) => {
        const app = await buildApp(options);
        replaceClose(app, async (original) => {
          await original();
          throw cleanupFailure;
        });
        return app;
      },
    });

    expect(code).toBe(1);
    expect(harness.lines).toEqual([
      "Signal registration and application cleanup both failed.",
      registrationFailure.message,
      cleanupFailure.message,
    ]);
  });

  it("removes handlers and reports a signal-owned close failure once", async () => {
    const harness = await shutdownHarness();
    const source = new FakeShutdownSignalSource();
    const cleanupFailure = new Error("simulated signal cleanup failure");
    let closeCalls = 0;

    const code = await runCli(["serve", "--port", "8765"], {
      ...harness.context,
      shutdownSignalSource: source,
      serve: {
        owner: "cli-owned",
        run: async (app) => {
          replaceClose(app, async (original) => {
            closeCalls += 1;
            await original();
            throw cleanupFailure;
          });
          source.emit("SIGINT");
          source.emit("SIGTERM");
        },
      },
    });

    expect(code).toBe(1);
    expect(closeCalls).toBe(1);
    expect(harness.lines).toEqual([cleanupFailure.message]);
    expect(source.listenerCount("SIGINT")).toBe(0);
    expect(source.listenerCount("SIGTERM")).toBe(0);
  });
});
