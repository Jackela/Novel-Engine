import { afterEach, describe, expect, it, vi } from "vitest";

import {
  TextGenerationCancelledError,
  type TextGenerationTask,
} from "../../src/contexts/ai/application/ports/text_generation.js";
import { DeterministicStoryProvider } from "../../src/contexts/ai/infrastructure/providers/deterministic_story_provider.js";
import type { ProviderTransport } from "../../src/contexts/ai/infrastructure/providers/provider_http.js";
import {
  dispatchProviderResponse,
  startProviderResponseDeadline,
} from "../../src/contexts/ai/infrastructure/providers/provider_response_lifecycle.js";

function chapterTask(): TextGenerationTask {
  return {
    step: "chapter_draft",
    systemPrompt: "system prompt",
    userPrompt: "write a chapter",
    responseSchema: { chapter_markdown: { type: "string" } },
    metadata: { chapter_number: 2 },
  };
}

function lateResponseHarness(): {
  readonly transport: ProviderTransport;
  readonly resolve: (response: Response) => void;
} {
  let resolveResponse: ((response: Response) => void) | undefined;
  const transport: ProviderTransport = () =>
    new Promise<Response>((resolve) => {
      resolveResponse = resolve;
    });
  return {
    transport,
    resolve: (response) => {
      if (resolveResponse === undefined) throw new Error("transport did not dispatch");
      resolveResponse(response);
    },
  };
}

function responseWithCancelSpy(cancel: () => void): Response {
  return new Response(new ReadableStream<Uint8Array>({ cancel }), { status: 200 });
}

afterEach(() => {
  vi.useRealTimers();
});

describe("provider response cleanup races", () => {
  it("cancels a late response after external cancellation wins dispatch", async () => {
    const controller = new AbortController();
    const deadline = startProviderResponseDeadline("late external", 60, controller.signal);
    const late = lateResponseHarness();
    const pending = dispatchProviderResponse(
      late.transport,
      "https://provider.example/late",
      {},
      "late external",
      deadline,
    );
    const settled = expect(pending).rejects.toThrow(TextGenerationCancelledError);

    controller.abort();
    await settled;
    const cancel = vi.fn();
    late.resolve(responseWithCancelSpy(cancel));

    await vi.waitFor(() => expect(cancel).toHaveBeenCalledTimes(1));
    deadline.finish();
  });

  it("cancels a late response after the absolute deadline wins dispatch", async () => {
    vi.useFakeTimers();
    const deadline = startProviderResponseDeadline("late deadline", 1);
    const late = lateResponseHarness();
    const pending = dispatchProviderResponse(
      late.transport,
      "https://provider.example/late",
      {},
      "late deadline",
      deadline,
    );
    const settled = expect(pending).rejects.toThrow(/timed out after 1s/);

    await vi.advanceTimersByTimeAsync(1_000);
    await settled;
    const cancel = vi.fn();
    late.resolve(responseWithCancelSpy(cancel));
    await vi.advanceTimersByTimeAsync(0);

    expect(cancel).toHaveBeenCalledTimes(1);
    deadline.finish();
  });

  it("reports no deterministic outcome when cancellation follows the final delta", async () => {
    const provider = new DeterministicStoryProvider();
    const baseline: string[] = [];
    for await (const delta of provider.generateStructuredStreaming(chapterTask())) {
      baseline.push(delta);
    }
    const controller = new AbortController();
    let outcomes = 0;
    const stream = provider.generateStructuredStreaming(chapterTask(), {
      signal: controller.signal,
      onOutcome: () => {
        outcomes += 1;
      },
    });

    for (let index = 0; index < baseline.length; index += 1) {
      const step = await stream.next();
      expect(step.done).toBe(false);
      if (index === baseline.length - 1) controller.abort();
    }

    await expect(stream.next()).resolves.toEqual({ done: true, value: undefined });
    expect(outcomes).toBe(0);
  });
});
