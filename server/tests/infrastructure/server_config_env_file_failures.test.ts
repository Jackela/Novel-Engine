import { mkdtemp, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ConfigurationError,
  loadServerConfig,
} from "../../src/shared/infrastructure/config/server_config.js";

const environmentFileHarness = vi.hoisted(() => ({
  parserFailure: undefined as Error | undefined,
  readFailure: undefined as Error | undefined,
  statFailure: undefined as Error | undefined,
}));

vi.mock("node:fs", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:fs")>();
  return {
    ...actual,
    readFileSync: (...args: unknown[]) => {
      if (environmentFileHarness.readFailure !== undefined) {
        throw environmentFileHarness.readFailure;
      }
      return Reflect.apply(actual.readFileSync, actual, args);
    },
    statSync: (...args: unknown[]) => {
      if (environmentFileHarness.statFailure !== undefined) {
        throw environmentFileHarness.statFailure;
      }
      return Reflect.apply(actual.statSync, actual, args);
    },
  };
});

vi.mock("../../src/shared/infrastructure/config/env_file.js", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../src/shared/infrastructure/config/env_file.js")>();
  return {
    ...actual,
    parseEnvFile: (text: string) => {
      if (environmentFileHarness.parserFailure !== undefined) {
        throw environmentFileHarness.parserFailure;
      }
      return actual.parseEnvFile(text);
    },
  };
});

afterEach(() => {
  environmentFileHarness.parserFailure = undefined;
  environmentFileHarness.readFailure = undefined;
  environmentFileHarness.statFailure = undefined;
});

async function makeWorkspace(): Promise<string> {
  return mkdtemp(join(tmpdir(), "novel-engine-env-file-"));
}

function captureError(run: () => unknown): unknown {
  try {
    run();
  } catch (error) {
    return error;
  }
  return undefined;
}

describe("optional environment-file failures", () => {
  it("keeps a missing environment file optional", async () => {
    const workspace = await makeWorkspace();

    const config = loadServerConfig({
      env: { APP_ENVIRONMENT: "testing" },
      envFile: join(workspace, "missing.env.local"),
      workingDirectory: workspace,
    });

    expect(config.environment).toBe("testing");
  });

  it("rejects a directory with a stable configuration error", async () => {
    const workspace = await makeWorkspace();

    const error = captureError(() =>
      loadServerConfig({
        env: { APP_ENVIRONMENT: "testing" },
        envFile: workspace,
        workingDirectory: workspace,
      }),
    );

    expect(error).toBeInstanceOf(ConfigurationError);
    expect(error).toMatchObject({
      message: `Environment file must be a regular file: ${workspace}`,
    });
  });

  it("accepts a symbolic link to a regular environment file", async () => {
    const workspace = await makeWorkspace();
    const target = join(workspace, "settings.env");
    const envFile = join(workspace, ".env.local");
    await writeFile(target, "APP_ENVIRONMENT=testing\n");
    await symlink(target, envFile);

    const config = loadServerConfig({ env: {}, envFile, workingDirectory: workspace });

    expect(config.environment).toBe("testing");
  });

  it("rethrows the same non-missing stat failure object", async () => {
    const workspace = await makeWorkspace();
    const envFile = join(workspace, ".env.local");
    await writeFile(envFile, "APP_ENVIRONMENT=testing\n");
    const statFailure = Object.assign(new Error("environment file metadata denied"), {
      code: "EACCES",
    });
    environmentFileHarness.statFailure = statFailure;

    const error = captureError(() =>
      loadServerConfig({
        env: { APP_ENVIRONMENT: "development" },
        envFile,
        workingDirectory: workspace,
      }),
    );

    expect(error).toBe(statFailure);
  });

  it("rethrows the same non-missing read failure object", async () => {
    const workspace = await makeWorkspace();
    const envFile = join(workspace, ".env.local");
    await writeFile(envFile, "APP_ENVIRONMENT=testing\n");
    const readFailure = Object.assign(new Error("environment file access denied"), {
      code: "EACCES",
    });
    environmentFileHarness.readFailure = readFailure;

    const error = captureError(() =>
      loadServerConfig({
        env: { APP_ENVIRONMENT: "testing" },
        envFile,
        workingDirectory: workspace,
      }),
    );

    expect(error).toBe(readFailure);
  });

  it("rethrows the same parser failure even when it resembles a missing-file error", async () => {
    const workspace = await makeWorkspace();
    const envFile = join(workspace, ".env.local");
    await writeFile(envFile, "APP_ENVIRONMENT=testing\n");
    const parserFailure = Object.assign(new Error("environment parser failed"), {
      code: "ENOENT",
    });
    environmentFileHarness.parserFailure = parserFailure;

    const error = captureError(() =>
      loadServerConfig({
        env: { APP_ENVIRONMENT: "development" },
        envFile,
        workingDirectory: workspace,
      }),
    );

    expect(error).toBe(parserFailure);
  });
});
