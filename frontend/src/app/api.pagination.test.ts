import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Studio API pagination requests", () => {
  it("encodes bounded revision query options without leaking them into fetch", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ revisions: [], next_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.revisions("project-1", "document-1", {
        limit: 50,
        cursor: "a/b+=",
        signal: controller.signal,
      }),
    ).resolves.toEqual({ revisions: [], next_cursor: null });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1/revisions?limit=50&cursor=a%2Fb%2B%3D",
      expect.objectContaining({ credentials: "include" }),
    );
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init).not.toHaveProperty("limit");
    expect(init).not.toHaveProperty("cursor");
  });

  it.each([0, 101, 1.5])("rejects the out-of-range revision page limit %s", async (limit) => {
    vi.stubGlobal("fetch", vi.fn());

    expect(() => api.revisions("project-1", "document-1", { limit })).toThrow(
      "Revision page limit must be an integer from 1 through 100.",
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("encodes bounded jobs query options without changing read transport semantics", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ jobs: [], next_cursor: "next" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      api.jobs("project-1", { limit: 25, cursor: "a/b+=", signal: controller.signal }),
    ).resolves.toEqual({ jobs: [], next_cursor: "next" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/jobs?limit=25&cursor=a%2Fb%2B%3D",
      expect.objectContaining({ credentials: "include" }),
    );
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(init).not.toHaveProperty("limit");
    expect(init).not.toHaveProperty("cursor");
    expect(init?.signal).not.toBe(controller.signal);
  });
});
