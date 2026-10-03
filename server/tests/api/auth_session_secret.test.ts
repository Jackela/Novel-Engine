import { readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";
import { SESSION_SECRET_FILE_NAME } from "../../src/shared/infrastructure/config/session_secret.js";
import {
  cookieHeader,
  cookieJar,
  loginOwner,
  makeDataDirectory,
  setupOwner,
} from "./auth_helpers.js";

/**
 * DR-040: a non-container start without `SECURITY_SECRET_KEY` persists the
 * generated key to `<dataDirectory>/.secret` (0600, created once, reused), so
 * a restart no longer logs the author out. Production/staging keep the
 * existing guard behavior and are pinned in auth_session.test.ts.
 */
async function openApp(directory: string, sessionSecret?: string) {
  return buildApp({
    logger: false,
    databasePath: join(directory, "novel-engine.sqlite3"),
    environment: "development",
    ...(sessionSecret === undefined ? {} : { sessionSecret }),
  });
}

async function loginJar(directory: string, sessionSecret?: string): Promise<Map<string, string>> {
  const app = await openApp(directory, sessionSecret);
  try {
    await setupOwner(app);
    return cookieJar(await loginOwner(app));
  } finally {
    await app.close();
  }
}

function secretFilePath(directory: string): string {
  return join(directory, SESSION_SECRET_FILE_NAME);
}

async function sessionStatus(
  directory: string,
  jar: Map<string, string>,
  sessionSecret?: string,
): Promise<number> {
  const app = await openApp(directory, sessionSecret);
  try {
    const response = await app.inject({
      method: "GET",
      url: "/api/session",
      headers: { cookie: cookieHeader(jar) },
    });
    return response.statusCode;
  } finally {
    await app.close();
  }
}

describe("generated session secret persistence (DR-040)", () => {
  it("keeps owner sessions across a restart without a configured secret", async () => {
    const directory = await makeDataDirectory();
    const jar = await loginJar(directory);

    expect(await sessionStatus(directory, jar)).toBe(200);
  });

  it("persists the generated secret in a 0600 file that later starts reuse", async () => {
    const directory = await makeDataDirectory();
    await loginJar(directory);

    const path = secretFilePath(directory);
    const stats = statSync(path);
    expect(stats.isFile()).toBe(true);
    expect(stats.mode & 0o777).toBe(0o600);
    const persisted = readFileSync(path, "utf8").trim();
    expect(persisted.length).toBeGreaterThanOrEqual(32);

    // A later start must reuse the same key rather than mint a new one.
    const jar = await loginJar(directory);
    expect(readFileSync(path, "utf8").trim()).toBe(persisted);
    expect(await sessionStatus(directory, jar)).toBe(200);
  });

  it("lets an explicitly configured secret win over the persisted file", async () => {
    const directory = await makeDataDirectory();
    const persistedJar = await loginJar(directory);
    const path = secretFilePath(directory);
    const persistedSecret = readFileSync(path, "utf8").trim();

    // A configured secret replaces the persisted one for that process only.
    expect(await sessionStatus(directory, persistedJar, "explicit-session-secret-alpha")).toBe(401);
    expect(readFileSync(path, "utf8").trim()).toBe(persistedSecret);
    // The persisted key survives untouched: dropping the explicit secret
    // restores the original sessions instead of rotating them.
    expect(await sessionStatus(directory, persistedJar)).toBe(200);
  });

  it("refuses to start on an empty persisted secret instead of rotating it", async () => {
    const directory = await makeDataDirectory();
    await loginJar(directory);
    writeFileSync(secretFilePath(directory), "\n", "utf8");

    await expect(openApp(directory)).rejects.toThrow(/is empty/);
  });

  it("writes no secret file for a production deployment", async () => {
    const directory = await makeDataDirectory();
    const app = await buildApp({
      logger: false,
      environment: "production",
      databasePath: join(directory, "novel-engine.sqlite3"),
    });
    await app.close();

    expect(() => statSync(secretFilePath(directory))).toThrow(/ENOENT/);
  });
});
