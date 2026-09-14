import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

const statsPayload = {
  project_id: "project-1",
  daily: [
    {
      date: "2026-09-13",
      words: { author: 500, ai_accepted: 300, restore: -100 },
    },
    {
      date: "2026-09-14",
      words: { author: 220, ai_accepted: 0, restore: 0 },
    },
  ],
  weekly: [
    {
      start_date: "2026-09-08",
      words: { author: 720, ai_accepted: 300, restore: -100 },
    },
  ],
  streak_days: 3,
  chapters: { total: 10, started: 7 },
  usage: {
    project_id: "project-1",
    request_count: 4,
    prompt_tokens: 300,
    completion_tokens: 100,
    per_model: [{ model: "mock-model", requests: 4, prompt_tokens: 300, completion_tokens: 100 }],
    daily: [
      {
        date: "2026-09-14",
        request_count: 4,
        prompt_tokens: 300,
        completion_tokens: 100,
      },
    ],
  },
};

function respondWith(payload: unknown): void {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("writing stats API contract (#653)", () => {
  it("preserves every field family through the real api.writingStats boundary", async () => {
    respondWith(statsPayload);

    await expect(api.writingStats("project-1")).resolves.toEqual(statsPayload);
  });

  it("requires usage.daily on the stats endpoint even though the shared schema keeps it optional", async () => {
    // The wire schema reuses the usage endpoint's declaration, where `daily`
    // stays optional for older usage responses. The stats endpoint itself
    // always ships it: `usageWirePayload` maps `aggregateProjectUsage`
    // verbatim and that aggregation zero-fills all 30 UTC days. Parsing it
    // as required here locks that implementation behavior — a stats payload
    // without usage daily buckets is a server regression, not a legacy
    // shape to render.
    const { daily: _legacyOptional, ...usageWithoutDaily } = statsPayload.usage;
    respondWith({ ...statsPayload, usage: usageWithoutDaily });

    await expect(api.writingStats("project-1")).rejects.toThrow(
      "Invalid writing stats response.usage.daily",
    );
  });

  it.each([
    [
      "daily words author",
      {
        daily: [
          { ...statsPayload.daily[0], words: { ...statsPayload.daily[0].words, author: "500" } },
        ],
      },
      "Invalid writing stats response.daily[0].words.author",
    ],
    [
      "weekly start_date",
      { weekly: [{ words: statsPayload.weekly[0].words }] },
      "Invalid writing stats response.weekly[0].start_date",
    ],
    [
      "chapters total",
      { chapters: { ...statsPayload.chapters, total: null } },
      "Invalid writing stats response.chapters.total",
    ],
    [
      "usage per_model row",
      {
        usage: {
          ...statsPayload.usage,
          per_model: [{ ...statsPayload.usage.per_model[0], requests: "4" }],
        },
      },
      "Invalid writing stats response.usage.per_model[0].requests",
    ],
    ["streak_days", { streak_days: "3" }, "Invalid writing stats response.streak_days"],
  ])(
    "rejects a malformed payload (%s) at the API boundary",
    async (_label, override, expectedError) => {
      respondWith({ ...statsPayload, ...override });

      await expect(api.writingStats("project-1")).rejects.toThrow(expectedError);
    },
  );
});
