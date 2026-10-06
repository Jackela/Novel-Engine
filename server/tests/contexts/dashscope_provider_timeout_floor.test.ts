import { describe, expect, it, vi } from "vitest";

import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import {
  chapterTask,
  generationBody,
  jsonResponse,
  provider,
} from "./dashscope_provider.test-helpers.js";

describe("dashscope long-form timeout floor", () => {
  it("grants chapter steps at least 180 seconds via the abort signal", async () => {
    vi.useFakeTimers();
    try {
      let requestDispatched = false;
      let abortFired = false;
      const transport: ProviderTransport = (_url, init) => {
        requestDispatched = true;
        return new Promise<Response>((resolve) => {
          init?.signal?.addEventListener(
            "abort",
            () => {
              abortFired = true;
              resolve(jsonResponse(200, generationBody('{"chapter_markdown": "late"}')));
            },
            { once: true },
          );
        });
      };
      const generation = provider({
        transport,
        timeoutSeconds: 30,
        retry: { maxAttempts: 1, delayMs: 0, sleep: async () => {} },
      }).generateStructured(chapterTask("chapter_revision"));
      const settled = expect(generation).rejects.toThrow(/timed out after 180s/);

      expect(requestDispatched).toBe(true);
      await vi.advanceTimersByTimeAsync(179_999);
      expect(abortFired).toBe(false);
      await vi.advanceTimersByTimeAsync(1);
      expect(abortFired).toBe(true);
      await settled;
    } finally {
      vi.useRealTimers();
    }
  });

  it("grants an editorial review the same 180-second floor instead of the 30s base (DR-025)", async () => {
    vi.useFakeTimers();
    try {
      let transportCalls = 0;
      let abortFired = false;
      const transport: ProviderTransport = (_url, init) => {
        transportCalls += 1;
        return new Promise<Response>((resolve) => {
          init?.signal?.addEventListener(
            "abort",
            () => {
              abortFired = true;
              resolve(jsonResponse(200, generationBody("{}")));
            },
            { once: true },
          );
        });
      };
      const generation = provider({
        transport,
        timeoutSeconds: 30,
        retry: { maxAttempts: 1, delayMs: 0, sleep: async () => {} },
      }).generateStructured({ ...chapterTask("editorial_review") });
      const settled = expect(generation).rejects.toThrow(/timed out after 180s/);

      expect(transportCalls).toBe(1);
      await vi.advanceTimersByTimeAsync(29_999);
      expect(abortFired).toBe(false);
      await vi.advanceTimersByTimeAsync(150_000);
      expect(abortFired).toBe(false);
      await vi.advanceTimersByTimeAsync(1);
      expect(abortFired).toBe(true);
      await settled;
    } finally {
      vi.useRealTimers();
    }
  });
});
