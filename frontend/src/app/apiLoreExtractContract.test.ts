import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

/**
 * A terminal lore-extract job payload as the synchronous route answers it
 * (#614): complete Job fields, the candidate set riding `result`, and the
 * chronological event trail.
 */
function loreExtractJob(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    id: "job-1",
    project_id: "project-1",
    document_id: null,
    kind: "lore-extract",
    operation: "extract",
    status: "completed",
    provider: "mock",
    model: "scripted-model",
    request: { segment: "Mira keeps the ledger" },
    result: {
      candidates: [
        {
          kind: "character",
          title: "Mira",
          aliases: ["The Clerk"],
          summary: "Keeps the ledger.",
        },
      ],
    },
    error: null,
    retry_of_job_id: null,
    events: [
      {
        id: "event-1",
        status: "completed",
        details: { candidates_count: 1 },
        created_at: "2026-09-14T00:00:00.000Z",
      },
    ],
    created_at: "2026-09-14T00:00:00.000Z",
    updated_at: "2026-09-14T00:00:00.000Z",
    ...overrides,
  };
}

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

describe("lore extraction API contract (#614)", () => {
  it("preserves the terminal job and its candidate set through the real api.extractLore boundary", async () => {
    respondWith(loreExtractJob());

    const job = await api.extractLore("project-1", "Mira keeps the ledger", "mock");

    expect(job.kind).toBe("lore-extract");
    expect(job.status).toBe("completed");
    expect(job.result.candidates).toEqual([
      { kind: "character", title: "Mira", aliases: ["The Clerk"], summary: "Keeps the ledger." },
    ]);
    expect(job.events[0]).toMatchObject({ status: "completed" });
  });

  it("passes a provider-failed terminal job through as the wizard's segment failure", async () => {
    respondWith(
      loreExtractJob({
        status: "failed",
        model: "",
        result: { candidates: [] },
        error: "provider transport failed",
        events: [
          { id: "event-1", status: "failed", details: {}, created_at: "2026-09-14T00:00:00.000Z" },
        ],
      }),
    );

    const job = await api.extractLore("project-1", "text", "mock");

    expect(job.status).toBe("failed");
    expect(job.error).toBe("provider transport failed");
    expect(job.result.candidates).toEqual([]);
  });

  it.each([
    ["wrong kind", { kind: "proposal" }, "Invalid lore extraction job.kind"],
    ["missing candidates", { result: {} }, "Invalid lore extraction job.result.candidates"],
    [
      "candidate kind",
      {
        result: {
          candidates: [{ kind: "note", title: "Mira", aliases: [], summary: "text" }],
        },
      },
      "Invalid lore extraction job.result.candidates[0].kind",
    ],
    [
      "candidate alias row",
      {
        result: {
          candidates: [{ kind: "world", title: "Flood Market", aliases: [7], summary: "text" }],
        },
      },
      "Invalid lore extraction job.result.candidates[0].aliases[0]",
    ],
    ["status", { status: "running" }, "Invalid lore extraction job.status"],
  ])(
    "rejects a malformed payload (%s) at the API boundary",
    async (_label, override, expectedError) => {
      respondWith(loreExtractJob(override));

      await expect(api.extractLore("project-1", "text", "mock")).rejects.toThrow(expectedError);
    },
  );
});
