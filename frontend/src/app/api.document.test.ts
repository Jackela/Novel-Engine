import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("current Document API", () => {
  it("reads exactly one current Document from its scoped resource", async () => {
    const payload = {
      id: "document-1",
      project_id: "project-1",
      kind: "chapter",
      title: "Chapter 1",
      position: 0,
      volume_id: null,
      beat_ref: null,
      lore_status: null,
      current_revision_id: "revision-1",
      content_markdown: "Accepted body",
      metadata: {},
      revision_source: "author",
      word_count: 2,
      created_at: "2026-09-03T00:00:00Z",
      updated_at: "2026-09-03T00:00:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.document("project-1", "document-1")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/documents/document-1",
      expect.objectContaining({ credentials: "include" }),
    );
  });
});
