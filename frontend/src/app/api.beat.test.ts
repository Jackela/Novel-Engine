import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

function okResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("chapter beat API (#466)", () => {
  it("links a beat with PUT, CSRF, and credentials semantics", async () => {
    vi.stubGlobal("document", { cookie: "novel_engine_csrf=test-csrf-token" });
    const view = { beat: { title: "The Storm", content: "washed-up chart" } };
    const fetchMock = vi.fn().mockResolvedValue(okResponse(view));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.linkChapterBeat("project-1", "document-1", "The Storm")).resolves.toEqual(
      view,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1/beat",
      expect.objectContaining({
        method: "PUT",
        credentials: "include",
        body: JSON.stringify({ beat: "The Storm" }),
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-CSRF-Token": "test-csrf-token",
        }),
      }),
    );
  });

  it("clears the association with an explicit null beat body", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse({ beat: null }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.linkChapterBeat("project-1", "document-1", null)).resolves.toEqual({
      beat: null,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1/beat",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ beat: null }),
      }),
    );
  });

  it("rejects a malformed resolved-beat envelope", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(okResponse({ beat: { title: 7, content: "washed-up chart" } }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.linkChapterBeat("project-1", "document-1", "The Storm")).rejects.toThrow(
      "Invalid chapter beat response.beat.title",
    );
  });
});
