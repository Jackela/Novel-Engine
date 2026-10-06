import { existsSync, mkdtempSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import {
  armFirstBootSetupToken,
  SETUP_TOKEN_FILENAME,
} from "../../src/shared/infrastructure/db/setup_token.js";

function scratchDirectory(): string {
  return mkdtempSync(join(tmpdir(), "novel-engine-setup-token-"));
}

function failOnWarning(message: string): never {
  throw new Error(`unexpected setup-token warning: ${message}`);
}

describe("first-boot setup token file", () => {
  it("creates a 0600 token file while no owner exists and verifies it", () => {
    const directory = scratchDirectory();
    const reported: string[] = [];
    const guard = armFirstBootSetupToken({
      directory,
      ownerExists: false,
      onToken: (token) => reported.push(token),
      onWarning: failOnWarning,
    });

    const tokenPath = join(directory, SETUP_TOKEN_FILENAME);
    expect(reported).toHaveLength(1);
    expect(readFileSync(tokenPath, "utf8").trim()).toBe(reported[0]);
    expect(statSync(tokenPath).mode & 0o777).toBe(0o600);
    expect(guard.verify(reported[0])).toBe(true);
    expect(guard.verify("wrong-token")).toBe(false);
    expect(guard.verify(undefined)).toBe(false);
  });

  it("reuses the persisted token across restarts so the logged value stays valid", () => {
    const directory = scratchDirectory();
    const first: string[] = [];
    const second: string[] = [];
    armFirstBootSetupToken({
      directory,
      ownerExists: false,
      onToken: (token) => first.push(token),
      onWarning: failOnWarning,
    });
    armFirstBootSetupToken({
      directory,
      ownerExists: false,
      onToken: (token) => second.push(token),
      onWarning: failOnWarning,
    });

    expect(second).toEqual(first);
  });

  it("removes a stale token file and disarms once an owner exists", () => {
    const directory = scratchDirectory();
    const tokenPath = join(directory, SETUP_TOKEN_FILENAME);
    writeFileSync(tokenPath, "stale-token\n", { mode: 0o600 });
    const reported: string[] = [];
    const guard = armFirstBootSetupToken({
      directory,
      ownerExists: true,
      onToken: (token) => reported.push(token),
      onWarning: failOnWarning,
    });

    expect(existsSync(tokenPath)).toBe(false);
    expect(reported).toEqual([]);
    expect(guard.verify("stale-token")).toBe(false);
  });

  it("invalidates the token and deletes the file after a successful setup", () => {
    const directory = scratchDirectory();
    const reported: string[] = [];
    const guard = armFirstBootSetupToken({
      directory,
      ownerExists: false,
      onToken: (token) => reported.push(token),
      onWarning: failOnWarning,
    });

    guard.invalidate();
    guard.invalidate();

    expect(existsSync(join(directory, SETUP_TOKEN_FILENAME))).toBe(false);
    expect(guard.verify(reported[0])).toBe(false);
  });
});
