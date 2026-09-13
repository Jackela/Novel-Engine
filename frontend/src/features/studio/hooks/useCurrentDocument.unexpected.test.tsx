import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { DocumentSummary } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";

import { useCurrentDocument } from "./useCurrentDocument";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      document: vi.fn<typeof actual.api.document>(),
      project: vi.fn<typeof actual.api.project>(),
    },
  };
});

const accepted = chapter("document-1", {
  volume_id: null,
  current_revision_id: "revision-1",
  content_markdown: "Accepted body",
});
const { content_markdown: _content, metadata: _metadata, ...summary } = accepted;
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});

describe("useCurrentDocument unexpected failures", () => {
  it("reports one shared cycle rejection and gives every subscriber local Retry state", async () => {
    const reportError = vi.fn();
    vi.stubGlobal("reportError", reportError);
    vi.mocked(api.document).mockResolvedValue({
      ...accepted,
      current_revision_id: "revision-2",
    });
    const lifecycle = Symbol("shared unexpected lifecycle");
    const owner = {
      summary,
      lifecycle,
      captureProjectShellRead: () => {
        throw new Error("broken shell authority");
      },
      publishProjectShellRead: vi.fn(() => true),
      onSessionLoss: vi.fn(),
      onProjectMissing: vi.fn(),
    };
    let first: ReturnType<typeof useCurrentDocument> | undefined;
    let second: ReturnType<typeof useCurrentDocument> | undefined;

    function First(): null {
      first = useCurrentDocument("project-1", owner);
      return null;
    }
    function Second(): null {
      second = useCurrentDocument("project-1", owner);
      return null;
    }
    harness.mount(
      <>
        <First />
        <Second />
      </>,
    );
    await flushEffects();
    await flushEffects();

    expect(reportError).toHaveBeenCalledTimes(1);
    expect(reportError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "broken shell authority" }),
    );
    expect(first).toMatchObject({ isLoading: false, error: expect.stringContaining("unexpected") });
    expect(second).toMatchObject({
      isLoading: false,
      error: expect.stringContaining("unexpected"),
    });
    expect(api.document).toHaveBeenCalledTimes(1);
    expect(api.project).not.toHaveBeenCalled();
  });

  it("reports a shell publication throw and leaves a bounded local failure", async () => {
    const reportError = vi.fn();
    vi.stubGlobal("reportError", reportError);
    const raced = { ...accepted, current_revision_id: "revision-2" };
    const refreshedSummary: DocumentSummary = {
      ...summary,
      current_revision_id: "revision-2",
    };
    vi.mocked(api.document).mockResolvedValue(raced);
    vi.mocked(api.project).mockResolvedValue(projectWith([refreshedSummary]));
    const owner = {
      summary,
      lifecycle: Symbol("publication failure lifecycle"),
      captureProjectShellRead: () => ({
        projectId: "project-1",
        readEpoch: 1,
        mutationEpoch: 0,
      }),
      publishProjectShellRead: () => {
        throw new Error("broken shell publication");
      },
      onSessionLoss: vi.fn(),
      onProjectMissing: vi.fn(),
    };
    let current: ReturnType<typeof useCurrentDocument> | undefined;
    function Probe(): null {
      current = useCurrentDocument("project-1", owner);
      return null;
    }
    harness.mount(<Probe />);
    await flushEffects();
    await flushEffects();

    expect(reportError).toHaveBeenCalledTimes(1);
    expect(reportError).toHaveBeenCalledWith(
      expect.objectContaining({ message: "broken shell publication" }),
    );
    expect(current).toMatchObject({
      isLoading: false,
      error: expect.stringContaining("unexpected"),
    });
    expect(api.document).toHaveBeenCalledTimes(1);
    expect(api.project).toHaveBeenCalledTimes(1);
  });
});
