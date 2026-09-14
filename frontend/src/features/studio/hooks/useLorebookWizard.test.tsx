import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { LoreExtractCandidate } from "@/app/types/lore";
import type { StudioJob } from "@/app/types/studio";
import { createMountHarness, deferred } from "@/test/harness";

import { useLorebookWizard } from "./useLorebookWizard";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      extractLore: vi.fn<typeof actual.api.extractLore>(),
      createDocument: vi.fn<typeof actual.api.createDocument>(),
      saveDocumentAliases: vi.fn<typeof actual.api.saveDocumentAliases>(),
    },
  };
});

type HookResult = ReturnType<typeof useLorebookWizard>;

const mountHarness = createMountHarness();

afterEach(() => {
  mountHarness.cleanup();
  vi.resetAllMocks();
});

function loreJob(
  candidates: LoreExtractCandidate[],
  overrides: Partial<StudioJob> = {},
): StudioJob {
  return {
    id: "job-1",
    project_id: "project-1",
    document_id: null,
    kind: "lore-extract",
    operation: "extract",
    status: "completed",
    provider: "mock",
    model: "scripted-model",
    request: {},
    result: { candidates },
    error: null,
    retry_of_job_id: null,
    events: [],
    created_at: "2026-09-14T00:00:00.000Z",
    updated_at: "2026-09-14T00:00:00.000Z",
    ...overrides,
  };
}

function candidate(
  kind: LoreExtractCandidate["kind"],
  title: string,
  aliases: string[],
): LoreExtractCandidate {
  return { kind, title, aliases, summary: `${title} summary.` };
}

function renderWizardHook() {
  let current: HookResult | undefined;
  function Harness(): null {
    current = useLorebookWizard("project-1", "mock");
    return null;
  }
  mountHarness.mount(<Harness />);
  return {
    result: (): HookResult => {
      if (current === undefined) throw new Error("Expected wizard hook result after render.");
      return current;
    },
  };
}

async function submit(hook: HookResult, text: string): Promise<void> {
  await act(async () => {
    await hook.submitSegment(text, "Pasted text");
  });
}

describe("useLorebookWizard", () => {
  it("submits each segment as its own extraction job and merges completed results", async () => {
    vi.mocked(api.extractLore)
      .mockResolvedValueOnce(
        loreJob([
          candidate("character", "Mira", ["The Clerk"]),
          candidate("world", "Flood Market", ["Market"]),
        ]),
      )
      .mockResolvedValueOnce(loreJob([candidate("character", "Mira", ["Ledger Keeper"])]));
    const hook = renderWizardHook();

    await submit(hook.result(), "segment one");
    await submit(hook.result(), "segment two");

    expect(api.extractLore).toHaveBeenCalledTimes(2);
    expect(vi.mocked(api.extractLore).mock.calls.map((call) => call[1])).toEqual([
      "segment one",
      "segment two",
    ]);
    expect(hook.result().segments.map((segment) => segment.status)).toEqual([
      "completed",
      "completed",
    ]);
    // Same (kind, title) collapses with the union of aliases, ordered by
    // kind then title.
    expect(hook.result().candidates).toEqual([
      {
        key: "character\nMira",
        kind: "character",
        title: "Mira",
        aliases: ["The Clerk", "Ledger Keeper"],
        summary: "Mira summary.",
        segmentCount: 2,
      },
      {
        key: "world\nFlood Market",
        kind: "world",
        title: "Flood Market",
        aliases: ["Market"],
        summary: "Flood Market summary.",
        segmentCount: 1,
      },
    ]);
  });

  it("keeps the merge deterministic: recomputing over the same completed segments yields the same list", async () => {
    vi.mocked(api.extractLore).mockResolvedValue(
      loreJob([candidate("world", "Zeta", ["z"]), candidate("character", "Ada", ["a"])]),
    );
    const hook = renderWizardHook();
    await submit(hook.result(), "s1");
    const first = hook.result().candidates;
    // Any state change (selection toggle) recomputes the merged view.
    act(() => {
      hook.result().toggleCandidate("character\nAda");
    });
    expect(hook.result().candidates).toEqual(first);
    expect(hook.result().selectedCandidates.map((entry) => entry.title)).toEqual(["Zeta"]);
  });

  it("guards against duplicate submission of an identical in-flight paste", async () => {
    const pending = deferred<StudioJob>();
    vi.mocked(api.extractLore).mockReturnValueOnce(pending.promise);
    const hook = renderWizardHook();

    await act(async () => {
      void hook.result().submitSegment("same text", "Pasted text");
      await Promise.resolve();
    });
    await act(async () => {
      await hook.result().submitSegment("same text", "Pasted text");
    });

    expect(api.extractLore).toHaveBeenCalledTimes(1);
    await act(async () => {
      pending.resolve(loreJob([]));
      await Promise.resolve();
    });
  });

  it("records a failed job or transport error per segment and recovers through retry", async () => {
    vi.mocked(api.extractLore)
      .mockResolvedValueOnce(loreJob([], { status: "failed", error: "provider unavailable" }))
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(loreJob([candidate("world", "Flood Market", ["Market"])]));
    const hook = renderWizardHook();

    await submit(hook.result(), "first");
    await submit(hook.result(), "second");

    expect(hook.result().segments.map((segment) => segment.status)).toEqual(["failed", "failed"]);
    expect(hook.result().segments.map((segment) => segment.error)).toEqual([
      "provider unavailable",
      "network down",
    ]);
    expect(hook.result().candidates).toEqual([]);

    const failedId = hook.result().segments[0]?.id;
    if (failedId === undefined) throw new Error("Expected the first segment id.");
    await act(async () => {
      await hook.result().retrySegment(failedId);
    });

    expect(api.extractLore).toHaveBeenCalledTimes(3);
    expect(hook.result().segments[0]).toMatchObject({ status: "completed" });
    expect(hook.result().candidates.map((entry) => entry.title)).toEqual(["Flood Market"]);
  });

  it("abandons the session on reset, clearing segments, candidates, and selection", async () => {
    vi.mocked(api.extractLore).mockResolvedValue(loreJob([candidate("character", "Mira", [])]));
    const hook = renderWizardHook();
    await submit(hook.result(), "text");
    expect(hook.result().candidates).toHaveLength(1);

    act(() => {
      hook.result().reset();
    });

    expect(hook.result().segments).toEqual([]);
    expect(hook.result().candidates).toEqual([]);
    expect(hook.result().results).toEqual([]);
    expect(api.createDocument).not.toHaveBeenCalled();
  });

  it("confirms selected candidates through creation then alias write and reports partial success", async () => {
    vi.mocked(api.extractLore).mockResolvedValue(
      loreJob([
        candidate("character", "Mira", ["The Clerk"]),
        candidate("world", "Ridge", ["Pass"]),
      ]),
    );
    vi.mocked(api.createDocument).mockResolvedValueOnce({
      id: "doc-ridge",
    } as Awaited<ReturnType<typeof api.createDocument>>);
    const aliasWrite = vi.mocked(api.saveDocumentAliases);
    aliasWrite.mockRejectedValueOnce(new Error("alias write failed"));
    const hook = renderWizardHook();
    await submit(hook.result(), "text");
    act(() => {
      hook.result().toggleCandidate("character\nMira");
    });

    await act(async () => {
      await hook.result().confirmSelected();
    });

    expect(api.createDocument).toHaveBeenCalledTimes(1);
    expect(api.createDocument).toHaveBeenCalledWith("project-1", {
      kind: "world",
      title: "Ridge",
      content_markdown: "Ridge summary.",
    });
    expect(aliasWrite).toHaveBeenCalledWith("project-1", "doc-ridge", ["Pass"]);
    expect(hook.result().results).toEqual([
      {
        key: "world\nRidge",
        kind: "world",
        title: "Ridge",
        aliases: ["Pass"],
        outcome: "created-with-failed-aliases",
        error: "alias write failed",
        documentId: "doc-ridge",
      },
    ]);

    // The retry keeps the aliases and upgrades the outcome on success.
    aliasWrite.mockResolvedValueOnce({ aliases: [] } as Awaited<
      ReturnType<typeof api.saveDocumentAliases>
    >);
    await act(async () => {
      await hook.result().retryAliases("world\nRidge");
    });
    expect(aliasWrite).toHaveBeenLastCalledWith("project-1", "doc-ridge", ["Pass"]);
    expect(hook.result().results[0]).toMatchObject({ outcome: "created", error: null });
  });
});
