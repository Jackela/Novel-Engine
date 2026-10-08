import { afterEach, expect, it, vi } from "vitest";
import { HttpError } from "./httpClient";
import { observeAiOperation } from "./observeAiOperation";

afterEach(() => vi.unstubAllGlobals());

it("waits for ready and forwards a split permission event without revealing private fields", async () => {
  const encoder = new TextEncoder();
  const received: unknown[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"type":"ready","operation_id":"op"}\n\n'));
            controller.enqueue(
              encoder.encode(
                'data: {"type":"permission","permission_id":"p","tool":{"title":"Write notes","kind":"edit","target":"notes.md"},"options":[',
              ),
            );
            controller.enqueue(
              encoder.encode(
                '{"option_id":"allow","name":"Allow once","kind":"allow_once"}],"raw_stdout":"secret"}\n\n',
              ),
            );
            controller.enqueue(
              encoder.encode('data: {"type":"completed","external_effects":"none"}\n\n'),
            );
            controller.close();
          },
        }),
      ),
    ),
  );
  const observation = observeAiOperation({
    projectId: "project",
    operationId: "op",
    signal: new AbortController().signal,
    onEvent: (event) => received.push(event),
  });
  await observation.ready;
  await observation.done;
  expect(fetch).toHaveBeenCalledWith(
    "/api/projects/project/ai-operations/op/events",
    expect.objectContaining({ credentials: "include" }),
  );
  expect(received).toEqual([
    { type: "ready", operation_id: "op" },
    {
      type: "permission",
      permission_id: "p",
      tool: { title: "Write notes", kind: "edit", target: "notes.md" },
      options: [{ option_id: "allow", name: "Allow once", kind: "allow_once" }],
    },
    { type: "completed", external_effects: "none" },
  ]);
});

function eventResponse(events: readonly unknown[]) {
  return new Response(events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""));
}
it("rejects an expired owner session before ready with the typed HTTP error", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: "UNAUTHENTICATED", message: "Sign in again" } }),
          { status: 401 },
        ),
      ),
  );
  const observation = observeAiOperation({
    projectId: "p",
    operationId: "op",
    signal: new AbortController().signal,
    onEvent: vi.fn(),
  });
  const ready = observation.ready.catch((error: unknown) => error);
  const done = observation.done.catch((error: unknown) => error);
  expect(await ready).toBeInstanceOf(HttpError);
  expect(await done).toMatchObject({ status: 401, code: "UNAUTHENTICATED" });
});
it.each(
  [
    [{ type: "ready", operation_id: "other" }],
    [{ type: "tool", tool_id: "t", title: "Read", kind: "read", status: "pending" }],
    [
      { type: "ready", operation_id: "op" },
      { type: "thinking", text: "private" },
    ],
    [{ type: "ready", operation_id: "op" }],
  ].map((events) => ({ events })),
)(
  "treats mismatched, unannounced, private, and truncated streams as failed observation",
  async ({ events }) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(eventResponse(events)));
    const observation = observeAiOperation({
      projectId: "p",
      operationId: "op",
      signal: new AbortController().signal,
      onEvent: vi.fn(),
    });
    const ready = observation.ready.catch(() => undefined);
    const done = observation.done.catch((error: unknown) => error);
    await ready;
    expect(await done).toBeInstanceOf(Error);
  },
);
it("cancels the reader when the owner leaves a ready observation", async () => {
  const cancel = vi.fn();
  const encoder = new TextEncoder();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.enqueue(encoder.encode('data: {"type":"ready","operation_id":"op"}\n\n'));
          },
          cancel,
        }),
      ),
    ),
  );
  const controller = new AbortController();
  const observation = observeAiOperation({
    projectId: "p",
    operationId: "op",
    signal: controller.signal,
    onEvent: vi.fn(),
  });
  const done = observation.done.catch((error: unknown) => error);
  await observation.ready;
  controller.abort();
  expect(await done).toBeInstanceOf(Error);
  expect(cancel).toHaveBeenCalledTimes(1);
});
it("reports a transport failure without sending a generation request", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
  const observation = observeAiOperation({
    projectId: "p",
    operationId: "op",
    signal: new AbortController().signal,
    onEvent: vi.fn(),
  });
  const ready = observation.ready.catch((error: unknown) => error);
  const done = observation.done.catch((error: unknown) => error);
  expect(await ready).toBeInstanceOf(Error);
  expect(await done).toMatchObject({ cause: expect.any(TypeError) });
});
