import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { buildApp } from "../../src/apps/api/app.js";

const INDEX_HTML = "<!doctype html><html><body>studio shell</body></html>";
const ASSET_JS = "console.log('app bundle');";
const SECRET_OUTSIDE_DIST = "token-that-must-never-be-served";

interface SpaFixture {
  distDirectory: string;
  cleanup: () => void;
}

function buildSpaFixture(): SpaFixture {
  const parent = mkdtempSync(join(tmpdir(), "ne-spa-"));
  const dist = join(parent, "dist");
  mkdirSync(join(dist, "assets"), { recursive: true });
  writeFileSync(join(dist, "index.html"), INDEX_HTML);
  writeFileSync(join(dist, "assets", "index-AbC123.js"), ASSET_JS);
  writeFileSync(join(dist, "favicon.svg"), "<svg></svg>");
  writeFileSync(join(parent, "secret.txt"), SECRET_OUTSIDE_DIST);
  symlinkSync(join(parent, "secret.txt"), join(dist, "assets", "outside.js"));
  return { distDirectory: dist, cleanup: () => rmSync(parent, { recursive: true, force: true }) };
}

describe("SPA serving surface", () => {
  const fixture = buildSpaFixture();
  let app: Awaited<ReturnType<typeof buildApp>>;

  beforeAll(async () => {
    app = await buildApp({ logger: false, spaDistDirectory: fixture.distDirectory });
  });

  afterAll(async () => {
    await app.close();
    fixture.cleanup();
  });

  it("serves the SPA shell at the root without long caching", async () => {
    const response = await app.inject({ method: "GET", url: "/" });

    expect(response.statusCode).toBe(200);
    expect(response.headers["content-type"]).toContain("text/html");
    expect(response.body).toBe(INDEX_HTML);
    expect(response.headers["cache-control"]).not.toContain("immutable");
  });

  it("serves deep links through the SPA fallback", async () => {
    const response = await app.inject({
      method: "GET",
      url: "/projects/9f2c7a41-6c50-4d12-9a41-0f2a91aa62d1/documents",
    });

    expect(response.statusCode).toBe(200);
    expect(response.body).toBe(INDEX_HTML);
  });

  it("serves hashed assets with a long immutable cache policy", async () => {
    const response = await app.inject({ method: "GET", url: "/assets/index-AbC123.js" });

    expect(response.statusCode).toBe(200);
    expect(response.body).toBe(ASSET_JS);
    const cacheControl = String(response.headers["cache-control"]);
    expect(cacheControl).toContain("max-age=31536000");
    expect(cacheControl).toContain("immutable");
  });

  it("serves unhashed root files without the immutable policy", async () => {
    const response = await app.inject({ method: "GET", url: "/favicon.svg" });

    expect(response.statusCode).toBe(200);
    expect(response.headers["cache-control"]).not.toContain("immutable");
  });

  it("keeps missing and out-of-root assets on the normal 404 envelope", async () => {
    const missing = await app.inject({ method: "GET", url: "/assets/missing.js" });
    expect(missing.statusCode).toBe(404);
    expect(missing.json()).toMatchObject({ error: { code: "NOT_FOUND" } });

    const outside = await app.inject({ method: "GET", url: "/assets/outside.js" });
    expect(outside.statusCode).toBe(404);
    expect(outside.json()).toMatchObject({ error: { code: "NOT_FOUND" } });
    expect(outside.body).not.toContain(SECRET_OUTSIDE_DIST);
  });

  it("keeps API and operational routes distinct from the SPA", async () => {
    const unknownApi = await app.inject({ method: "GET", url: "/api/not-a-route" });
    expect(unknownApi.statusCode).toBe(404);
    expect(unknownApi.json()).toMatchObject({ error: { code: "NOT_FOUND" } });

    const health = await app.inject({ method: "GET", url: "/health/live" });
    expect(health.statusCode).toBe(200);

    const version = await app.inject({ method: "GET", url: "/version" });
    expect(version.statusCode).toBe(200);

    const openapi = await app.inject({ method: "GET", url: "/openapi.json" });
    expect(openapi.statusCode).toBe(200);

    const unknownOpenapi = await app.inject({ method: "GET", url: "/openapi.jsonx" });
    expect(unknownOpenapi.statusCode).toBe(404);
    expect(unknownOpenapi.json()).toMatchObject({ error: { code: "NOT_FOUND" } });
  });

  it("keeps unknown non-GET requests on the API 404 envelope", async () => {
    const response = await app.inject({ method: "POST", url: "/projects/somewhere" });

    expect(response.statusCode).toBe(404);
    expect(response.json()).toMatchObject({ error: { code: "NOT_FOUND" } });
  });

  it("does not serve files from outside the dist root", async () => {
    const encoded = await app.inject({ method: "GET", url: "/..%2Fsecret.txt" });
    expect(encoded.statusCode).toBe(404);
    expect(encoded.json()).toMatchObject({ error: { code: "NOT_FOUND" } });

    const plain = await app.inject({ method: "GET", url: "/../secret.txt" });
    expect(plain.statusCode).toBe(404);
    expect(plain.json()).toMatchObject({ error: { code: "NOT_FOUND" } });
    expect(plain.body).not.toContain(SECRET_OUTSIDE_DIST);
  });
});

describe("SPA serving without a built dist (API-only mode)", () => {
  it("boots and explains the missing build instead of serving HTML", async () => {
    const app = await buildApp({
      logger: false,
      spaDistDirectory: join(tmpdir(), "ne-spa-does-not-exist"),
    });

    try {
      const root = await app.inject({ method: "GET", url: "/" });
      expect(root.statusCode).toBe(200);
      expect(root.json()).toEqual({
        name: "Novel Engine",
        version: root.json().version,
        message: "Build frontend/ to enable the Studio UI.",
      });

      const deepLink = await app.inject({ method: "GET", url: "/projects/anything" });
      expect(deepLink.statusCode).toBe(200);
      expect(deepLink.json().message).toBe("Build frontend/ to enable the Studio UI.");

      const health = await app.inject({ method: "GET", url: "/health/live" });
      expect(health.statusCode).toBe(200);

      const unknownApi = await app.inject({ method: "GET", url: "/api/not-a-route" });
      expect(unknownApi.statusCode).toBe(404);
      expect(unknownApi.json()).toMatchObject({ error: { code: "NOT_FOUND" } });
    } finally {
      await app.close();
    }
  });
});
