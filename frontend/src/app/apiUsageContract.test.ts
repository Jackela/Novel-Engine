import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

const usagePayload = {
  project_id: "project-1",
  request_count: 3,
  prompt_tokens: 10,
  completion_tokens: 20,
  per_model: [{ model: "mock-model", requests: 3, prompt_tokens: 10, completion_tokens: 20 }],
  daily: [{ date: "2026-09-08", request_count: 3, prompt_tokens: 10, completion_tokens: 20 }],
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("usage API contract", () => {
  it("preserves daily buckets through the real api.usage boundary", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(usagePayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(api.usage("project-1")).resolves.toMatchObject({ daily: usagePayload.daily });
  });

  it("keeps daily optional for older usage responses", async () => {
    const { daily: _daily, ...legacyPayload } = usagePayload;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(legacyPayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await api.usage("project-1");
    expect(result.project_id).toBe("project-1");
    expect(result.daily).toBeUndefined();
  });

  it.each([
    ["date", { date: 20260908 }],
    ["request_count", { request_count: "3" }],
    ["prompt_tokens", { prompt_tokens: null }],
  ])("rejects malformed daily bucket %s at the API boundary", async (field, override) => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            ...usagePayload,
            daily: [{ ...usagePayload.daily[0], ...override }],
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      ),
    );

    await expect(api.usage("project-1")).rejects.toThrow(`Invalid daily[0].${field}`);
  });
});
