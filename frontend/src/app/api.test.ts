import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { appConfig } from "./config";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Studio API client", () => {
  it("preserves unified revision conflict code and details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            error: {
              code: "REVISION_CONFLICT",
              message: "Document changed since the requested base revision.",
              details: { current_revision_id: "revision-b" },
            },
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const request = api.saveDocument("project", "document", {
      content_markdown: "stale",
      base_revision_id: "revision-a",
    });
    await expect(request).rejects.toMatchObject({
      status: 409,
      code: "REVISION_CONFLICT",
      detail: expect.objectContaining({ current_revision_id: "revision-b" }),
    });
  });

  it("ignores the retired Python detail error payload", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: {
              message: "Document changed since the requested base revision.",
              current_revision_id: "revision-b",
            },
          }),
          { status: 409, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const request = api.saveDocument("project", "document", {
      content_markdown: "stale",
      base_revision_id: "revision-a",
    });
    await expect(request).rejects.toMatchObject({
      status: 409,
      detail: undefined,
    });
  });

  it("falls back to the status message for unrecognised error bodies", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ unexpected: "shape" }), {
          status: 422,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const error = await api.projects().catch((reason: unknown) => reason);
    expect(error).toMatchObject({
      message: "Request failed with status 422",
      status: 422,
    });
  });

  it.each([
    ["JSON request", () => api.projects()],
    ["download", () => api.download("/api/exports/example/download")],
  ])("uses the injected product name when a %s cannot reach the server", async (_label, run) => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network unavailable")));

    await expect(run()).rejects.toThrow(
      "Test Engine is unavailable. Check the local service and retry.",
    );
  });

  it("propagates caller cancellation through the internal request signal", async () => {
    const controller = new AbortController();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_input: RequestInfo | URL, init?: RequestInit) =>
          new Promise((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () => {
              reject(new DOMException("Aborted", "AbortError"));
            });
          }),
      ),
    );

    const pending = api.projects({ signal: controller.signal });
    controller.abort();

    const error = await pending.catch((reason: unknown) => reason);
    expect(error).toMatchObject({ message: "Request cancelled." });
  });

  it("keeps create-export POST and CSRF semantics when forwarding caller cancellation", async () => {
    const controller = new AbortController();
    vi.stubGlobal("document", { cookie: "novel_engine_csrf=test-csrf-token" });
    const fetchMock = vi.fn(
      (_input: RequestInfo | URL, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const pending = api.createExport("project-1", "docx", { signal: controller.signal });
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/exports",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        body: JSON.stringify({ format: "docx" }),
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          "X-CSRF-Token": "test-csrf-token",
        }),
      }),
    );
    expect(init?.signal).not.toBe(controller.signal);

    controller.abort();

    await expect(pending).rejects.toMatchObject({ message: "Request cancelled." });
    expect(init?.signal?.aborted).toBe(true);
  });

  it("reports a caller-cancelled blob download as cancellation instead of timeout", async () => {
    const controller = new AbortController();
    const fetchMock = vi.fn(
      (_input: RequestInfo | URL, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("Aborted", "AbortError"));
          });
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const pending = api.download("/api/exports/export-1/download", {
      signal: controller.signal,
    });
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
    controller.abort();

    await expect(pending).rejects.toMatchObject({ message: "Request cancelled." });
    expect(init?.signal?.aborted).toBe(true);
  });

  it("preserves the blob download timeout error", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_input: RequestInfo | URL, init?: RequestInit) =>
          new Promise((_resolve, reject) => {
            init?.signal?.addEventListener("abort", () => {
              reject(new DOMException("Aborted", "AbortError"));
            });
          }),
      ),
    );

    const error = api.download("/api/exports/export-1/download").catch((reason: unknown) => reason);
    await vi.advanceTimersByTimeAsync(appConfig.apiTimeoutMs);

    await expect(error).resolves.toMatchObject({ message: "Download timed out. Please retry." });
  });

  it("sends X-CSRF-Token header on write requests when cookie is present", async () => {
    vi.stubGlobal("document", { cookie: "novel_engine_csrf=test-csrf-token" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "p1",
          title: "Title",
          description: "",
          settings: {},
          import_hash: null,
          created_at: "2026-06-25T00:00:00Z",
          updated_at: "2026-06-25T00:00:00Z",
          documents: [],
          volumes: [],
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.createProject("Title", "")).resolves.toMatchObject({
      id: "p1",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ "X-CSRF-Token": "test-csrf-token" }),
      }),
    );
  });

  it("does not send X-CSRF-Token header on read requests", async () => {
    vi.stubGlobal("document", { cookie: "novel_engine_csrf=test-csrf-token" });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ projects: [], next_cursor: null }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.projects()).resolves.toEqual({ projects: [], next_cursor: null });
    const init = fetchMock.mock.calls[0][1] as RequestInit | undefined;
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.["X-CSRF-Token"]).toBeUndefined();
  });

  it("does not authorize writes with the retired novel_studio_csrf cookie", async () => {
    vi.stubGlobal("document", {
      cookie: "novel_studio_csrf=legacy-csrf-token",
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "p1",
          title: "Title",
          description: "",
          settings: {},
          import_hash: null,
          created_at: "2026-06-25T00:00:00Z",
          updated_at: "2026-06-25T00:00:00Z",
          documents: [],
          volumes: [],
        }),
        {
          status: 201,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.createProject("Title", "")).resolves.toMatchObject({
      id: "p1",
    });
    const init = fetchMock.mock.calls[0][1] as RequestInit | undefined;
    const headers = init?.headers as Record<string, string> | undefined;
    expect(headers?.["X-CSRF-Token"]).toBeUndefined();
  });
});
