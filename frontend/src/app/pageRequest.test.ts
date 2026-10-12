import { afterEach, describe, expect, it, vi } from "vitest";

import { job, review } from "@/test/factories";

import { api } from "./api";
import type { PageRequestOptions } from "./pageRequest";

afterEach(() => {
  vi.unstubAllGlobals();
});

const pageRequests = [
  ["projects", (options: PageRequestOptions) => api.projects(options), "Project page"],
  ["jobs", (options: PageRequestOptions) => api.jobs("pro/ject", options), "Jobs page"],
  ["reviews", (options: PageRequestOptions) => api.reviews("pro/ject", options), "Review page"],
  ["exports", (options: PageRequestOptions) => api.exports("pro/ject", options), "Export page"],
  [
    "revisions",
    (options: PageRequestOptions) => api.revisions("pro/ject", "doc ument", options),
    "Revision page",
  ],
] as const;

describe("bounded API page requests (#479)", () => {
  it.each(pageRequests)(
    "validates the shared 1..100 limit for %s requests before transport",
    (_name, read, subject) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      for (const limit of [0, 101, 1.5]) {
        expect(() => read({ limit })).toThrow(
          `${subject} limit must be an integer from 1 through 100.`,
        );
      }
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it.each(pageRequests)(
    "encodes %s path and cursor without leaking pagination options into fetch",
    async (name, read) => {
      const payload = { [name]: [], next_cursor: null };
      const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)));
      vi.stubGlobal("fetch", fetchMock);
      const controller = new AbortController();

      await expect(
        read({
          limit: 100,
          cursor: "a/b+=",
          signal: controller.signal,
          headers: { "X-Request-Identity": "read-1" },
        }),
      ).resolves.toEqual(payload);

      const path =
        name === "projects"
          ? "/api/projects"
          : name === "revisions"
            ? "/api/projects/pro%2Fject/documents/doc%20ument/revisions"
            : `/api/projects/pro%2Fject/${name}`;
      expect(fetchMock).toHaveBeenCalledWith(
        `${path}?limit=100&cursor=a%2Fb%2B%3D`,
        expect.objectContaining({
          credentials: "include",
          headers: { "X-Request-Identity": "read-1" },
          signal: expect.any(AbortSignal),
        }),
      );
      const init = fetchMock.mock.calls[0]?.[1] as RequestInit | undefined;
      expect(init).not.toHaveProperty("limit");
      expect(init).not.toHaveProperty("cursor");
      expect(init?.signal).not.toBe(controller.signal);
    },
  );

  it.each([
    ["review", () => api.reviewDetail("pro/ject", "re view"), review()],
    ["retry", () => api.retryJob("pro/ject", "jo b", "key-1"), job()],
  ] as const)("encodes the %s request's opaque path identifiers", async (name, read, payload) => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload)));
    vi.stubGlobal("fetch", fetchMock);

    await read();

    expect(fetchMock).toHaveBeenCalledWith(
      name === "review"
        ? "/api/projects/pro%2Fject/reviews/re%20view"
        : "/api/projects/pro%2Fject/jobs/jo%20b/retry",
      expect.objectContaining({ credentials: "include" }),
    );
    if (name === "retry") {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({ "Idempotency-Key": "key-1" }),
        }),
      );
    }
  });
});
