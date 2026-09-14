import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { StudioJob } from "@/app/types/studio";
import { deferred } from "@/test/harness";

import {
  candidate,
  loreJob,
  submitSegment,
  wizardHookHarness,
} from "./useLorebookWizardTestHarness";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      extractLore: vi.fn<typeof actual.api.extractLore>(),
      createDocument: vi.fn<typeof actual.api.createDocument>(),
      saveDocumentAliases: vi.fn<typeof actual.api.saveDocumentAliases>(),
      document: vi.fn<typeof actual.api.document>(),
    },
  };
});

afterEach(() => {
  vi.resetAllMocks();
});

describe("useLorebookWizard segments", () => {
  it("submits each segment as its own extraction job and merges completed results", async () => {
    vi.mocked(api.extractLore)
      .mockResolvedValueOnce(
        loreJob([
          candidate("character", "Mira", ["The Clerk"]),
          candidate("world", "Flood Market", ["Market"]),
        ]),
      )
      .mockResolvedValueOnce(loreJob([candidate("character", "Mira", ["Ledger Keeper"])]));
    const hook = wizardHookHarness();
    try {
      await submitSegment(hook.result(), "segment one");
      await submitSegment(hook.result(), "segment two");

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
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("keeps the merge deterministic: recomputing over the same completed segments yields the same list", async () => {
    vi.mocked(api.extractLore).mockResolvedValue(
      loreJob([candidate("world", "Zeta", ["z"]), candidate("character", "Ada", ["a"])]),
    );
    const hook = wizardHookHarness();
    try {
      await submitSegment(hook.result(), "s1");
      const first = hook.result().candidates;
      // Any state change (selection toggle) recomputes the merged view.
      act(() => {
        hook.result().toggleCandidate("character\nAda");
      });
      expect(hook.result().candidates).toEqual(first);
      expect(hook.result().selectedCandidates.map((entry) => entry.title)).toEqual(["Zeta"]);
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("guards against duplicate submission of an identical in-flight paste", async () => {
    const pending = deferred<StudioJob>();
    vi.mocked(api.extractLore).mockReturnValueOnce(pending.promise);
    const hook = wizardHookHarness();
    try {
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
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("records a failed job or transport error per segment and recovers through retry", async () => {
    vi.mocked(api.extractLore)
      .mockResolvedValueOnce(loreJob([], { status: "failed", error: "provider unavailable" }))
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValueOnce(loreJob([candidate("world", "Flood Market", ["Market"])]));
    const hook = wizardHookHarness();
    try {
      await submitSegment(hook.result(), "first");
      await submitSegment(hook.result(), "second");

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
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("retries a failed document segment in place, re-reading its current content", async () => {
    vi.mocked(api.document)
      .mockRejectedValueOnce(new Error("document read failed"))
      .mockResolvedValueOnce({
        content_markdown: "the re-read chapter content",
      } as Awaited<ReturnType<typeof api.document>>);
    vi.mocked(api.extractLore).mockResolvedValueOnce(
      loreJob([candidate("world", "Flood Market", ["Market"])]),
    );
    const hook = wizardHookHarness();
    try {
      await act(async () => {
        await hook.result().submitDocumentSegment({ id: "doc-chapter-1", title: "Chapter 1" });
      });

      expect(hook.result().segments).toHaveLength(1);
      expect(hook.result().segments[0]).toMatchObject({
        documentId: "doc-chapter-1",
        status: "failed",
        error: "document read failed",
      });
      expect(api.extractLore).not.toHaveBeenCalled();

      const failedId = hook.result().segments[0]?.id;
      if (failedId === undefined) throw new Error("Expected the document segment id.");
      await act(async () => {
        await hook.result().retrySegment(failedId);
      });

      // The retry updates the same row — no appended ghost or duplicate row —
      // and extracts the re-read current content.
      expect(hook.result().segments).toHaveLength(1);
      expect(hook.result().segments[0]).toMatchObject({ status: "completed" });
      expect(api.extractLore).toHaveBeenCalledTimes(1);
      expect(api.extractLore).toHaveBeenCalledWith(
        "project-1",
        "the re-read chapter content",
        "mock",
      );
      expect(hook.result().candidates.map((entry) => entry.title)).toEqual(["Flood Market"]);
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("ignores a duplicate in-flight document submission for the same document", async () => {
    const pending = deferred<StudioJob>();
    const documentRead = deferred<{ content_markdown: string }>();
    vi.mocked(api.document).mockReturnValueOnce(documentRead.promise as never);
    vi.mocked(api.extractLore).mockReturnValueOnce(pending.promise);
    const hook = wizardHookHarness();
    try {
      await act(async () => {
        void hook.result().submitDocumentSegment({ id: "doc-chapter-1", title: "Chapter 1" });
        await Promise.resolve();
      });
      await act(async () => {
        await hook.result().submitDocumentSegment({ id: "doc-chapter-1", title: "Chapter 1" });
      });

      expect(api.document).toHaveBeenCalledTimes(1);
      await act(async () => {
        documentRead.resolve({ content_markdown: "text" });
        await Promise.resolve();
      });
      await act(async () => {
        pending.resolve(loreJob([]));
        await Promise.resolve();
      });
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("abandons the session on reset, clearing segments, candidates, and selection", async () => {
    vi.mocked(api.extractLore).mockResolvedValue(loreJob([candidate("character", "Mira", [])]));
    const hook = wizardHookHarness();
    try {
      await submitSegment(hook.result(), "text");
      expect(hook.result().candidates).toHaveLength(1);

      act(() => {
        hook.result().reset();
      });

      expect(hook.result().segments).toEqual([]);
      expect(hook.result().candidates).toEqual([]);
      expect(hook.result().results).toEqual([]);
      expect(api.createDocument).not.toHaveBeenCalled();
    } finally {
      hook.mountHarness.cleanup();
    }
  });
});
