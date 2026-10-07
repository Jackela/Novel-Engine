import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { ChapterBeatView } from "@/app/beatContract";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";

import { StudioBeatPanel } from "./StudioBeatPanel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();

  return {
    ...actual,
    api: {
      ...actual.api,
      chapterBeat: vi.fn<typeof actual.api.chapterBeat>(),
    },
  };
});

const harness = createMountHarness();

const CANDIDATES_VIEW: ChapterBeatView = {
  beat: null,
  candidates: [{ title: "The Harbor" }, { title: "The Storm" }],
  outline: { document_id: "outline-1", title: "Outline", outline_count: 1 },
};

beforeEach(() => {
  vi.mocked(api.chapterBeat).mockResolvedValue(CANDIDATES_VIEW);
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function panelFor(projectId: string) {
  return (
    <StudioBeatPanel projectId={projectId} documentId="doc-1" beatRef={null} onLink={vi.fn()} />
  );
}

function optionValues(container: HTMLDivElement): string[] {
  const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
  return Array.from(select.options).map((option) => option.value);
}

/**
 * DR-043 catalog scope: the panel's persistent owner outlives a project
 * switch, so the catalog must belong to the project the hook currently reads,
 * not to whichever project happened to answer last.
 */
describe("StudioBeatPanel catalog project scope (DR-043)", () => {
  it("drops the previous project's catalog when the project changes under the same document id", async () => {
    const nextProject = deferred<ChapterBeatView>();
    vi.mocked(api.chapterBeat).mockImplementation((projectId) =>
      projectId === "project-2" ? nextProject.promise : Promise.resolve(CANDIDATES_VIEW),
    );
    const { container, root } = harness.mount(panelFor("project-1"));
    await flushEffects();
    expect(optionValues(container)).toEqual(["", "The Harbor", "The Storm"]);

    // The same persistent panel now carries the next project with the same
    // document id, so the previous project's catalog must not stand in for the
    // new project's read.
    act(() => root.render(panelFor("project-2")));
    await flushEffects();
    expect(optionValues(container)).toEqual([""]);
    expect(getByRole(container, "button", { name: "Refresh beats" })).toBeDisabled();

    await act(async () => {
      nextProject.resolve({
        beat: null,
        candidates: [{ title: "The Tempest" }],
        outline: { document_id: "outline-2", title: "Second outline", outline_count: 1 },
      });
      await nextProject.promise;
    });
    expect(optionValues(container)).toEqual(["", "The Tempest"]);
  });

  it("never publishes a previous project's late read into the new project", async () => {
    const staleProject = deferred<ChapterBeatView>();
    const nextProject = deferred<ChapterBeatView>();
    vi.mocked(api.chapterBeat).mockImplementation((projectId) =>
      projectId === "project-1" ? staleProject.promise : nextProject.promise,
    );
    const { container, root } = harness.mount(panelFor("project-1"));
    await flushEffects();

    act(() => root.render(panelFor("project-2")));
    await flushEffects();
    await act(async () => {
      staleProject.resolve(CANDIDATES_VIEW);
      await staleProject.promise;
    });
    expect(optionValues(container)).toEqual([""]);

    await act(async () => {
      nextProject.resolve({
        beat: null,
        candidates: [{ title: "The Tempest" }],
        outline: { document_id: "outline-2", title: "Second outline", outline_count: 1 },
      });
      await nextProject.promise;
    });
    expect(optionValues(container)).toEqual(["", "The Tempest"]);
  });
});
