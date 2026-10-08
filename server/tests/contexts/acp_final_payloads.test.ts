import { link, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { AcpJsonResponse } from "../../src/contexts/ai/infrastructure/providers/AcpJsonResponse.js";
import { AcpTurnBudget } from "../../src/contexts/ai/infrastructure/providers/AcpTurnBudget.js";
import { AcpWorkspace } from "../../src/contexts/ai/infrastructure/providers/AcpWorkspace.js";

/** Validate the provider's declared structured shape, including nested candidates and strict field types. */
describe("ACP final payload and resource boundaries", () => {
  it.each([
    [
      {
        candidates: [
          { name: "string", confidence: "number", approved: "boolean", aliases: ["string"] },
        ],
      },
      { candidates: [{ name: "River", confidence: 0.8, approved: true, aliases: ["水流"] }] },
    ],
    [
      {
        findings: {
          type: "array",
          items: {
            type: "object",
            properties: { severity: { type: "string" }, position: { type: "integer" } },
          },
        },
      },
      { findings: [{ severity: "warning", position: 3 }] },
    ],
    [{ findings: [] }, { findings: [{ any: "unconstrained array item" }] }],
  ])("accepts a complete payload conforming to its declared schema", (schema, payload) => {
    const response = new AcpJsonResponse(schema);
    response.feed(JSON.stringify(payload));
    expect(JSON.parse(response.finish())).toEqual(payload);
    expect(response.feed(" \n")).toBeUndefined();
  });

  it.each([
    [
      "number-type",
      { candidates: [{ confidence: "number" }] },
      { candidates: [{ confidence: "0.8" }] },
    ],
    [
      "boolean-type",
      { candidates: [{ approved: "boolean" }] },
      { candidates: [{ approved: "true" }] },
    ],
    ["array-type", { findings: { type: "array", items: "string" } }, { findings: {} }],
    [
      "integer-type",
      { findings: [{ position: { type: "integer" } }] },
      { findings: [{ position: 1.5 }] },
    ],
    ["missing-field", { candidates: [{ name: "string" }] }, { candidates: [{}] }],
    ["extra-root", { findings: [] }, { findings: [], hidden: "extra payload" }],
  ])("rejects %s instead of coercing agent output", (_reason, schema, payload) => {
    const response = new AcpJsonResponse(schema);
    response.feed(JSON.stringify(payload));
    expect(() => response.finish()).toThrow("task schema");
  });

  it("refuses malformed JSON, unknown response roots and excessive progress", () => {
    const malformed = new AcpJsonResponse({ findings: [] });
    malformed.feed('{"findings":[NaN]}');
    expect(() => malformed.finish()).toThrow("not valid JSON");
    expect(() => new AcpJsonResponse({})).toThrow("known structured response key");
    expect(() => new AcpJsonResponse({ "findings-override": [] })).toThrow(
      "known structured response key",
    );
    const prefix = new AcpJsonResponse({ findings: [] });
    expect(() => prefix.feed("雪".repeat(22_000))).toThrow("progress prefix");
  });

  it("bounds the completed response even when incremental fragments individually fit", () => {
    const response = new AcpJsonResponse({ chapter_markdown: "string" });
    response.feed('{"chapter_markdown":"');
    expect(() => response.feed("x".repeat(16 * 1024 * 1024))).toThrow("response exceeds");
  });

  it("refuses hardlinked originals, oversized materials and non-directory workspaces", async () => {
    const directory = await mkdtemp(join(tmpdir(), "ne-acp-final-files-"));
    const original = join(directory, "original.md");
    const material = join(directory, "material.md");
    try {
      await writeFile(original, "Protected original");
      await link(original, material);
      const workspace = await AcpWorkspace.open(directory);
      await expect(workspace.read({ sessionId: "s", path: "material.md" })).rejects.toThrow(
        "unshared file",
      );
      await expect(
        workspace.write({ sessionId: "s", path: "material.md", content: "must not truncate" }),
      ).rejects.toThrow("unshared file");
      expect(await readFile(original, "utf8")).toBe("Protected original");
      const oversized = join(directory, "large.md");
      await writeFile(oversized, "x".repeat(1024 * 1024 + 1));
      await expect(workspace.read({ sessionId: "s", path: "large.md" })).rejects.toThrow(
        "byte budget",
      );
      await expect(
        workspace.write({ sessionId: "s", path: "new.md", content: "x".repeat(1024 * 1024 + 1) }),
      ).rejects.toThrow("byte budget");
      await expect(AcpWorkspace.open(original)).rejects.toThrow("not a directory");
      await expect(AcpWorkspace.open("relative/materials")).rejects.toThrow("must be absolute");
      await mkdir(join(directory, "folder"));
      await expect(workspace.read({ sessionId: "s", path: "folder" })).rejects.toThrow(
        "regular unshared file",
      );
      await expect(
        workspace.read({ sessionId: "s", path: "original.md/child.md" }),
      ).rejects.toThrow("directory alias");
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("reads a normal material with default and negative line bounds without exposing protected targets", async () => {
    const directory = await mkdtemp(join(tmpdir(), "ne-acp-final-lines-"));
    try {
      await writeFile(join(directory, "material.md"), "first\nsecond\nthird");
      const workspace = await AcpWorkspace.open(directory);
      expect(await workspace.read({ sessionId: "s", path: "material.md" })).toEqual({
        content: "first\nsecond\nthird",
      });
      expect(
        await workspace.read({ sessionId: "s", path: "material.md", line: -1, limit: 1 }),
      ).toEqual({ content: "first" });
      expect(workspace.safeTarget(workspace.root)).toBeUndefined();
      expect(workspace.safeTarget(undefined)).toBeUndefined();
    } finally {
      await rm(directory, { recursive: true, force: true });
    }
  });

  it("nested permission waits resume execution only after every waiter completes", async () => {
    vi.useFakeTimers();
    const budget = new AcpTurnBudget(30, 1000);
    try {
      budget.startExecution(30);
      budget.pause();
      budget.pause();
      await vi.advanceTimersByTimeAsync(100);
      expect(budget.signal.aborted).toBe(false);
      budget.resume();
      await vi.advanceTimersByTimeAsync(100);
      expect(budget.signal.aborted).toBe(false);
      budget.resume();
      const failed = expect(budget.wait(new Promise(() => {}))).rejects.toThrow("timeout");
      await vi.advanceTimersByTimeAsync(31);
      await failed;
    } finally {
      budget.close();
      vi.useRealTimers();
    }
  });

  it("a pre-cancelled budget rejects and consumes pending failures without scheduling work", async () => {
    const external = new AbortController();
    external.abort();
    const budget = new AcpTurnBudget(100, 1000, external.signal);
    try {
      await expect(
        budget.wait(Promise.reject(new Error("late pending rejection"))),
      ).rejects.toThrow("cancelled");
    } finally {
      budget.close();
    }
  });
});
