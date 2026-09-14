import { describe, expect, it } from "vitest";

import type { TextGenerationProviderFactory } from "../../src/contexts/ai/application/ports/text_generation.js";
import { DashScopeTextProvider } from "../../src/contexts/ai/infrastructure/providers/dashscope_provider.js";
import { loadServerConfig } from "../../src/shared/infrastructure/config/server_config.js";
import { readProductIdentity } from "../../src/shared/infrastructure/workspace_manifest.js";
import {
  fixtureApiKey,
  hostileProviderFailureBody,
  PROVIDER_FAILURE_CANARIES,
} from "../credential_fixtures.js";
import { propose } from "./proposal_test_helpers.js";
import { buildStudioApp, call, ownerJar, seedDocument, seedProject } from "./studio_helpers.js";

const MANUSCRIPT_CANARY = "DIAGNOSTICS_MANUSCRIPT_CANARY_CLOCKWORK";

/** Every object key reachable in the value, proving no error-code field ships. */
function collectKeys(value: unknown, into: Set<string> = new Set()): Set<string> {
  if (Array.isArray(value)) {
    for (const entry of value) collectKeys(entry, into);
  } else if (value !== null && typeof value === "object") {
    for (const [key, entry] of Object.entries(value)) {
      into.add(key);
      collectKeys(entry, into);
    }
  }
  return into;
}

/**
 * A DashScope provider whose transport answers hostile HTML carrying the
 * credential: the provider failure diagnostics boundary must discard the body
 * and persist only the normalized failure message.
 */
function hostileDashscopeFactory(
  apiKey: string,
  statusFor: (attempt: number) => number,
): {
  factory: TextGenerationProviderFactory;
} {
  let calls = 0;
  const transport = async () =>
    new Response(hostileProviderFailureBody(apiKey), {
      status: statusFor(calls++),
      headers: { "content-type": "text/html" },
    });
  const factory: TextGenerationProviderFactory = (requested) => {
    if (requested !== "dashscope") {
      throw new Error("Diagnostics fixture received an unexpected provider.");
    }
    return new DashScopeTextProvider({
      apiKey,
      retry: { delayMs: 0, sleep: async () => {} },
      transport,
    });
  };
  return { factory };
}

describe("opt-in diagnostics export (#654)", () => {
  it("exports the support field families with an explicit empty error state", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Support file");
      await seedDocument(app, jar, project.id, {
        kind: "chapter",
        title: "Canary Chapter",
        content_markdown: `${MANUSCRIPT_CANARY} The harbor kept its own time.`,
      });
      const identity = readProductIdentity();

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/diagnostics`);
      expect(response.statusCode, response.body).toBe(200);
      const body = response.json();
      expect(body).toEqual({
        generated_at: expect.any(String),
        product: { name: identity.name, version: identity.version },
        runtime: {
          platform: expect.any(String),
          architecture: expect.any(String),
          node_version: expect.any(String),
        },
        configuration: {
          provider: { id: "mock", label: "Mock (trial — no API key)", configured: true },
          keys: {
            session_secret: true,
            dashscope_api_key: false,
            openai_compatible_api_key: false,
          },
        },
        database: {
          quick_check: "ok",
          journal_mode: "wal",
          foreign_keys: true,
          owner_configured: true,
        },
        recent_errors: [],
      });
      expect(Number.isNaN(Date.parse(body.generated_at))).toBe(false);
      // The book stays out: no manuscript body, no document identity.
      expect(response.body).not.toContain(MANUSCRIPT_CANARY);
      expect(response.body).not.toContain("Canary Chapter");
    } finally {
      await app.close();
    }
  });

  it("keeps seeded secrets and discarded provider bodies out of the export", async () => {
    const sessionSecret = fixtureApiKey("diagnostics-session", "secret-that-must-not-leak");
    const dashscopeApiKey = fixtureApiKey("diagnostics-dashscope", "key-that-must-not-leak");
    const openaiApiKey = fixtureApiKey("diagnostics-openai", "key-that-must-not-leak");
    const fixture = hostileDashscopeFactory(dashscopeApiKey, () => 401);
    // Real-looking secrets enter through the resolved configuration seam
    // (env values only; no environment file) exactly as a deployment would.
    const config = loadServerConfig({
      envFile: null,
      env: {
        SECURITY_SECRET_KEY: sessionSecret,
        DASHSCOPE_API_KEY: dashscopeApiKey,
        LLM_API_KEY: openaiApiKey,
      },
    });
    const { app } = await buildStudioApp(undefined, {
      textProviderFactory: fixture.factory,
      config,
    });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Provider failure");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected a default document.");
      const failure = await propose(app, jar, project.id, document.id, {
        operation: "continue",
        provider: "dashscope",
      });
      expect(failure.statusCode, failure.body).toBe(200);
      expect(failure.json().status).toBe("failed");

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/diagnostics`);
      expect(response.statusCode, response.body).toBe(200);
      const body = response.json();
      // Credential state is booleans only, for every recognized key.
      expect(body.configuration.keys).toEqual({
        session_secret: true,
        dashscope_api_key: true,
        openai_compatible_api_key: true,
      });
      // The persisted failure message is the summary; nothing else of it ships.
      const error =
        "DashScope generation failed for step 'chapter_revision': provider returned HTTP 401.";
      expect(body.recent_errors).toEqual([{ message: error, occurred_at: expect.any(String) }]);
      for (const leaked of [
        sessionSecret,
        dashscopeApiKey,
        openaiApiKey,
        ...PROVIDER_FAILURE_CANARIES,
      ]) {
        expect(response.body).not.toContain(leaked);
      }
      // The envelope's response-time error code is not synthesized into the export.
      expect(collectKeys(body)).not.toContain("code");
    } finally {
      await app.close();
    }
  });

  it("scopes the recent error summary to the requesting project", async () => {
    const fixture = hostileDashscopeFactory(
      fixtureApiKey("diagnostics-scope", "key-that-must-not-leak"),
      () => 401,
    );
    const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
    try {
      const jar = await ownerJar(app);
      const quiet = await seedProject(app, jar, "Quiet project");
      const failing = await seedProject(app, jar, "Failing project");
      const document = failing.documents[0];
      if (document === undefined) throw new Error("Expected a default document.");
      const failure = await propose(app, jar, failing.id, document.id, {
        operation: "continue",
        provider: "dashscope",
      });
      expect(failure.statusCode, failure.body).toBe(200);

      const quietResponse = await call(app, jar, "GET", `/api/projects/${quiet.id}/diagnostics`);
      expect(quietResponse.statusCode, quietResponse.body).toBe(200);
      expect(quietResponse.json().recent_errors).toEqual([]);

      const failingResponse = await call(
        app,
        jar,
        "GET",
        `/api/projects/${failing.id}/diagnostics`,
      );
      expect(failingResponse.statusCode, failingResponse.body).toBe(200);
      expect(failingResponse.json().recent_errors).toHaveLength(1);
      // Another project's failure text never crosses the project boundary.
      expect(quietResponse.body).not.toContain("provider returned HTTP 401");
    } finally {
      await app.close();
    }
  });

  it("bounds the error summary to the most recent failures", async () => {
    const statuses = [401, 403, 404, 405, 406, 407, 409];
    const fixture = hostileDashscopeFactory(
      fixtureApiKey("diagnostics-window", "key-that-must-not-leak"),
      (attempt) => statuses[attempt] ?? 401,
    );
    const { app } = await buildStudioApp(undefined, { textProviderFactory: fixture.factory });
    try {
      const jar = await ownerJar(app);
      const project = await seedProject(app, jar, "Repeated failures");
      const document = project.documents[0];
      if (document === undefined) throw new Error("Expected a default document.");
      for (let attempt = 0; attempt < statuses.length; attempt += 1) {
        const failure = await propose(app, jar, project.id, document.id, {
          operation: "continue",
          provider: "dashscope",
        });
        expect(failure.statusCode, failure.body).toBe(200);
      }

      const response = await call(app, jar, "GET", `/api/projects/${project.id}/diagnostics`);
      expect(response.statusCode, response.body).toBe(200);
      const messages = response
        .json()
        .recent_errors.map((entry: { message: string }) => entry.message);
      expect(messages).toHaveLength(5);
      // Newest first: the last five attempts, in reverse call order.
      expect(messages).toEqual(
        [409, 407, 406, 405, 404].map(
          (status) =>
            `DashScope generation failed for step 'chapter_revision': provider returned HTTP ${status}.`,
        ),
      );
    } finally {
      await app.close();
    }
  });

  it("answers 401 unauthenticated and 404 for an unknown project", async () => {
    const { app } = await buildStudioApp();
    try {
      const jar = await ownerJar(app);
      await seedProject(app, jar, "Scoped");

      const anonymous = await app.inject({
        method: "GET",
        url: "/api/projects/p-1/diagnostics",
      });
      expect(anonymous.statusCode).toBe(401);
      expect(anonymous.json().error.code).toBe("UNAUTHORIZED");

      const unknown = await call(
        app,
        jar,
        "GET",
        "/api/projects/00000000-0000-0000-0000-000000000000/diagnostics",
      );
      expect(unknown.statusCode).toBe(404);
      expect(unknown.json().error.code).toBe("NOT_FOUND");
    } finally {
      await app.close();
    }
  });
});
