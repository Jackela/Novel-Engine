import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import type { AiExecutionOptions } from "@/app/AiExecutionOptions";
import { api, HttpError } from "@/app/api";
import type { AiOperationEvent } from "@/app/parseAiOperationEvent";
import { createMountHarness } from "@/test/harness";
import { useAcpOperation } from "./useAcpOperation";

const observations = vi.hoisted(() => new Map<string, (event: AiOperationEvent) => void>());
const control = vi.hoisted(() => ({
  holdReady: false,
  ready: new Map<string, () => void>(),
  done: new Map<string, () => void>(),
  fail: new Map<string, (reason: unknown) => void>(),
}));
vi.mock("@/app/observeAiOperation", () => ({
  observeAiOperation: (options: {
    operationId: string;
    onEvent: (event: AiOperationEvent) => void;
  }) => {
    observations.set(options.operationId, options.onEvent);
    return {
      ready: control.holdReady
        ? new Promise<void>((resolve) => control.ready.set(options.operationId, resolve))
        : Promise.resolve(),
      done: new Promise<void>((resolve, reject) => {
        control.done.set(options.operationId, resolve);
        control.fail.set(options.operationId, reject);
      }),
    };
  },
}));
const harness = createMountHarness();
afterEach(() => {
  harness.cleanup();
  observations.clear();
  control.holdReady = false;
  control.ready.clear();
  control.done.clear();
  control.fail.clear();
  vi.restoreAllMocks();
});

function mountOperation(onSessionLost?: () => void) {
  let model: ReturnType<typeof useAcpOperation> | undefined;
  function Harness() {
    model = useAcpOperation("project", onSessionLost);
    return null;
  }
  harness.mount(<Harness />);
  return () => {
    if (!model) throw new Error("Missing hook");
    return model;
  };
}
const permissionEvent = {
  type: "permission",
  permission_id: "permission",
  tool: { title: "Write notes", kind: "edit", target: "notes.md" },
  options: [{ option_id: "allow", name: "Allow once", kind: "allow_once" }],
} satisfies AiOperationEvent;

it("sends one permission decision even on rapid double activation and clears just that request", async () => {
  const respond = vi.spyOn(api, "respondAiPermission").mockResolvedValue();
  const model = mountOperation();
  const pending = model()
    .execute("acp", () => new Promise<void>(() => undefined))
    .catch(() => undefined);
  await act(async () => {
    await Promise.resolve();
  });
  const id = model().operations[0]?.id;
  if (!id) throw new Error("Missing operation");
  await act(async () => {
    observations.get(id)?.(permissionEvent);
  });
  await act(async () => {
    await Promise.all([
      model().respond(id, "permission", "allow"),
      model().respond(id, "permission", "allow"),
    ]);
  });
  expect(respond).toHaveBeenCalledTimes(1);
  expect(respond).toHaveBeenCalledWith(
    "project",
    id,
    "permission",
    "allow",
    expect.objectContaining({ signal: expect.any(AbortSignal) }),
  );
  expect(model().operations[0]?.permissions).toHaveLength(0);
  await act(async () => model().cancel(id));
  await pending;
});
it("keeps a failed decision available for retry and redirects when the owner session expires", async () => {
  const lost = vi.fn();
  const respond = vi
    .spyOn(api, "respondAiPermission")
    .mockRejectedValueOnce(new HttpError("Unavailable", 503))
    .mockRejectedValueOnce(new HttpError("Session expired", 401));
  const model = mountOperation(lost);
  const pending = model()
    .execute("acp", () => new Promise<void>(() => undefined))
    .catch(() => undefined);
  await act(async () => {
    await Promise.resolve();
  });
  const id = model().operations[0]?.id;
  if (!id) throw new Error("Missing operation");
  await act(async () => {
    observations.get(id)?.(permissionEvent);
    await model().respond(id, "permission", "allow");
  });
  expect(model().operations[0]?.permissions).toHaveLength(1);
  expect(model().operations[0]?.error).not.toBeNull();
  await act(async () => model().respond(id, "permission", "allow"));
  expect(respond).toHaveBeenCalledTimes(2);
  expect(lost).toHaveBeenCalledTimes(1);
  await pending;
});
it("aborts only the disconnected operation while preserving another operation's permission", async () => {
  const model = mountOperation();
  const calls = [1, 2].map(() =>
    model()
      .execute("acp", () => new Promise<void>(() => undefined))
      .catch(() => undefined),
  );
  await act(async () => {
    await Promise.resolve();
  });
  const [first, second] = model().operations;
  if (!first || !second) throw new Error("Missing operations");
  await act(async () => {
    observations.get(second.id)?.(permissionEvent);
    control.fail.get(first.id)?.(new HttpError("Connection lost", 503));
  });
  expect(model().operations.find((operation) => operation.id === first.id)?.phase).toBe("error");
  expect(
    model().operations.find((operation) => operation.id === second.id)?.permissions,
  ).toHaveLength(1);
  await act(async () => model().cancel(second.id));
  await Promise.all(calls);
});
it("keeps completed file action evidence when the author stops later work", async () => {
  const model = mountOperation();
  const pending = model()
    .execute("acp", () => new Promise<void>(() => undefined))
    .catch(() => undefined);
  await act(async () => {
    await Promise.resolve();
  });
  const id = model().operations[0]?.id;
  if (!id) throw new Error("Missing operation");
  await act(async () => {
    observations.get(id)?.({
      type: "tool",
      tool_id: "write",
      title: "Write notes",
      kind: "edit",
      status: "completed",
      target: "notes.md",
    });
    model().cancel(id);
  });
  expect(model().operations[0]?.effects).toBe("completed");
  expect(model().operations[0]?.tools[0]?.target).toBe("notes.md");
  await pending;
});

it("starts no generation before ready and waits for tool completion before settling the result", async () => {
  control.holdReady = true;
  const root = createRoot(document.createElement("div"));
  let model: ReturnType<typeof useAcpOperation> | undefined;
  function Harness() {
    model = useAcpOperation("project");
    return null;
  }
  await act(async () => root.render(<Harness />));
  if (!model) throw new Error("Missing hook");
  const request = vi
    .fn<(options?: AiExecutionOptions) => Promise<string>>()
    .mockResolvedValue("accepted response");
  let settled = false;
  const current = model;
  const results: Promise<string>[] = [];
  await act(async () => {
    results.push(
      current.execute("acp", request).then((value) => {
        settled = true;
        return value;
      }),
    );
  });
  expect(request).not.toHaveBeenCalled();
  const id = observations.keys().next().value;
  if (!id) throw new Error("Missing observer");
  await act(async () => {
    control.ready.get(id)?.();
  });
  expect(request).toHaveBeenCalledWith(
    expect.objectContaining({ headers: { "X-AI-Operation-Id": id }, timeoutMs: 610000 }),
  );
  expect(settled).toBe(false);
  await act(async () => {
    observations.get(id)?.({ type: "completed", external_effects: "none" });
    control.done.get(id)?.();
  });
  const result = results[0];
  if (result === undefined) throw new Error("Missing result");
  expect(await result).toBe("accepted response");
  expect(model?.operations[0]?.phase).toBe("completed");
  await act(async () => root.unmount());
});

it("keeps concurrent permission requests separate and cancels every pending operation on departure", async () => {
  const container = document.createElement("div");
  const root = createRoot(container);
  let model: ReturnType<typeof useAcpOperation> | undefined;
  function Harness() {
    model = useAcpOperation("project");
    return null;
  }
  await act(async () => root.render(<Harness />));
  if (!model) throw new Error("Missing hook");
  const current = model;
  const signals: AbortSignal[] = [];
  const calls = ["draft", "review"].map(() =>
    current
      .execute("acp", (options) => {
        if (!options?.signal) throw new Error("Missing operation signal");
        signals.push(options.signal);
        return new Promise<void>((_, reject) =>
          options.signal?.addEventListener("abort", () => reject(new Error("cancelled"))),
        );
      })
      .catch(() => undefined),
  );
  await act(async () => {
    await Promise.resolve();
  });
  await act(async () => {
    for (const [id, emit] of observations)
      emit({
        type: "permission",
        permission_id: id,
        tool: { title: "Write notes", kind: "edit" },
        options: [{ option_id: "allow", name: "Allow once", kind: "allow_once" }],
      });
  });
  await act(async () => {
    const first = observations.entries().next().value;
    if (!first) throw new Error("Missing observer");
    first[1]({
      type: "permission",
      permission_id: "second-for-first",
      tool: { title: "Write another file", kind: "edit" },
      options: [{ option_id: "allow", name: "Allow once", kind: "allow_once" }],
    });
  });
  expect(model?.operations.filter((operation) => operation.permissions.length > 0)).toHaveLength(2);
  expect(model?.operations.flatMap((operation) => operation.permissions)).toHaveLength(3);
  expect(signals.every((signal) => !signal.aborted)).toBe(true);
  await act(async () => root.unmount());
  await Promise.all(calls);
  expect(signals.every((signal) => signal.aborted)).toBe(true);
});
