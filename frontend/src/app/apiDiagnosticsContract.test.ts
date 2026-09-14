import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

const diagnosticsPayload = {
  generated_at: "2026-09-14T09:15:00Z",
  product: { name: "Novel Engine", version: "1.2.3" },
  runtime: { platform: "darwin", architecture: "arm64", node_version: "24.11.0" },
  configuration: {
    provider: { id: "mock", configured: true },
    keys: { session_secret: true, dashscope_api_key: false, openai_compatible_api_key: false },
  },
  database: {
    quick_check: "ok",
    journal_mode: "wal",
    foreign_keys: true,
    owner_configured: true,
  },
  recent_errors: [
    {
      message:
        "DashScope generation failed for step 'chapter_revision': provider returned HTTP 401.",
      occurred_at: "2026-09-14T09:04:00Z",
    },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("diagnostics API contract (#654)", () => {
  it("preserves the support field families through the real api boundary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(diagnosticsPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.diagnostics("project-1")).resolves.toEqual(diagnosticsPayload);
  });

  it.each([
    [
      "non-boolean key state",
      {
        configuration: {
          ...diagnosticsPayload.configuration,
          keys: { session_secret: "yes" },
        },
      },
    ],
    ["non-UTC generated_at", { generated_at: "2026-09-14 09:15:00" }],
    ["missing database health", { database: undefined }],
  ])("rejects a malformed payload (%s) at the API boundary", async (_label, override) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ ...diagnosticsPayload, ...override }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.diagnostics("project-1")).rejects.toThrow();
  });
});
