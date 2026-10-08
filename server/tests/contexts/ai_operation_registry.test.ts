import { describe, expect, it, vi } from "vitest";
import { AiOperationRegistry } from "../../src/contexts/ai/infrastructure/AiOperationRegistry.js";

describe("request-scoped AI interaction channel", () => {
  it("binds permissions to the owner, project and live operation, and refuses replay", async () => {
    const registry = new AiOperationRegistry();
    const scope = { ownerId: "owner", projectId: "project", operationId: "operation" };
    const events: unknown[] = [];
    const channel = registry.register(scope, (event) => events.push(event), vi.fn());
    expect(events).toEqual([{ type: "ready", operation_id: "operation" }]);
    const operation = registry.begin(scope);
    const pending = operation.execution.requestPermission?.({
      tool: { title: "Write material", kind: "edit" },
      options: [{ option_id: "allow", name: "Allow once", kind: "allow_once" }],
    });
    const permission = events[1] as { permission_id: string };
    expect(() =>
      registry.respond({ ...scope, ownerId: "other" }, permission.permission_id, "allow"),
    ).toThrow();
    registry.respond(scope, permission.permission_id, "allow");
    expect(await pending).toBe("allow");
    expect(() => registry.respond(scope, permission.permission_id, "allow")).toThrow();
    operation.finish();
    expect(events.at(-1)).toMatchObject({ type: "completed" });
    channel.close();
    registry.close();
  });
  it("expires unopened channels and cancels pending permission on observer disconnect", async () => {
    vi.useFakeTimers();
    const registry = new AiOperationRegistry(10, 20);
    const scope = { ownerId: "owner", projectId: "project", operationId: "expired" };
    registry.register(scope, vi.fn(), vi.fn());
    await vi.advanceTimersByTimeAsync(11);
    expect(() => registry.begin(scope)).toThrow();
    const active = { ...scope, operationId: "active" };
    const channel = registry.register(active, vi.fn(), vi.fn());
    const operation = registry.begin(active);
    const pending = operation.execution.requestPermission?.({
      tool: { title: "Read", kind: "read" },
      options: [],
    });
    channel.close();
    expect(await pending).toBeNull();
    expect(operation.execution.signal?.aborted).toBe(true);
    registry.close();
    vi.useRealTimers();
  });
});
