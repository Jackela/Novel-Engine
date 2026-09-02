import { describe, expect, it } from "vitest";

import { ExportRendererGuard } from "../../src/contexts/studio/application/export_renderer_guard.js";
import { OperationCapacityExceededError } from "../../src/contexts/studio/domain/exceptions.js";

describe("ExportRendererGuard", () => {
  it("admits one renderer and makes release exact-once and generation-safe", () => {
    const guard = new ExportRendererGuard();
    const first = guard.acquire("project-1");

    expect(() => guard.acquire("project-2")).toThrow(OperationCapacityExceededError);
    first.release();
    const second = guard.acquire("project-2");
    first.release();
    expect(() => guard.acquire("project-3")).toThrow(OperationCapacityExceededError);

    second.release();
    expect(() => guard.acquire("project-3")).not.toThrow();
  });
});
