import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";

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

/**
 * The wizard hook's confirmation half (#614): the two existing steps per
 * selected candidate, the honest partial-success reporting, and the
 * start-over semantics that keep the extracted segments reachable.
 */
describe("useLorebookWizard confirmation", () => {
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
    const hook = wizardHookHarness();
    try {
      await submitSegment(hook.result(), "text");
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
    } finally {
      hook.mountHarness.cleanup();
    }
  });

  it("starts a new run over the same segments after clearing results", async () => {
    vi.mocked(api.extractLore).mockResolvedValue(loreJob([candidate("character", "Mira", [])]));
    vi.mocked(api.createDocument).mockResolvedValue({
      id: "doc-mira",
    } as Awaited<ReturnType<typeof api.createDocument>>);
    vi.mocked(api.saveDocumentAliases).mockResolvedValue({ aliases: [] } as Awaited<
      ReturnType<typeof api.saveDocumentAliases>
    >);
    const hook = wizardHookHarness();
    try {
      await submitSegment(hook.result(), "text");
      await act(async () => {
        await hook.result().confirmSelected();
      });
      expect(hook.result().results).toHaveLength(1);

      act(() => {
        hook.result().clearResults();
      });

      // The confirmation clears, but the extracted segments — and the merged
      // candidates they fold into — stay reachable for another run.
      expect(hook.result().results).toEqual([]);
      expect(hook.result().segments).toHaveLength(1);
      expect(hook.result().candidates.map((entry) => entry.title)).toEqual(["Mira"]);
    } finally {
      hook.mountHarness.cleanup();
    }
  });
});
