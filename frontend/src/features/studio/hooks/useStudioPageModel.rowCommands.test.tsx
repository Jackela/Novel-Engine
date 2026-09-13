import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { StudioNavigator } from "../StudioNavigator";
import { resolveStudioRoute } from "../studioRouteState";
import { useStudioPageModel } from "./useStudioPageModel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn<typeof actual.api.project>(),
      document: vi.fn<typeof actual.api.document>(),
      providers: vi.fn<typeof actual.api.providers>(),
      jobs: vi.fn<typeof actual.api.jobs>(),
      revisions: vi.fn<typeof actual.api.revisions>(),
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
      deleteDocument: vi.fn<typeof actual.api.deleteDocument>(),
      moveChapterToVolume: vi.fn<typeof actual.api.moveChapterToVolume>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

const volumeOne = volume("volume-1", 1, { title: "Volume One" });
const volumeTwo = volume("volume-2", 2, { title: "Volume Two" });
const opening = chapter("doc-1", { title: "Opening", position: 1 });
const second = chapter("doc-2", { title: "Second", position: 2 });
const project = projectWith([opening, second], { volumes: [volumeOne, volumeTwo] });

function stubBootstrapReads(): void {
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.document).mockImplementation(async (_projectId, documentId) =>
    documentId === second.id ? second : opening,
  );
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.reviews).mockResolvedValue({ reviews: [], next_cursor: null });
  vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });
}

async function mountNavigatorPage() {
  const route = resolveStudioRoute(project.id, "manuscript", "");
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  function Probe() {
    current = useStudioPageModel(project.id, route, useNavigate());
    const navigator = current.viewProps?.navigator;
    return navigator ? <StudioNavigator {...navigator} /> : null;
  }
  const { container } = harness.mount(
    <MemoryRouter initialEntries={[route.canonicalPath]}>
      <Probe />
    </MemoryRouter>,
  );
  await flushEffects();
  const view = () => {
    if (!current?.viewProps) throw new Error("Expected a loaded Studio page model.");
    return current.viewProps;
  };
  return { container, view, model: () => current };
}

describe("Studio page model navigator row commands (#481)", () => {
  it("wires deletion end to end: confirm removes the row and falls back selection", async () => {
    stubBootstrapReads();
    vi.mocked(api.deleteDocument).mockResolvedValue(undefined);
    const { container, view, model } = await mountNavigatorPage();

    expect(getByRole(container, "button", { name: "Delete Opening" })).toBeDefined();
    act(() => fireEvent.click(getByRole(container, "button", { name: "Delete Opening" })));
    act(() => fireEvent.click(getByRole(container, "button", { name: "Confirm delete Opening" })));
    await flushEffects();

    expect(api.deleteDocument).toHaveBeenCalledWith(project.id, opening.id);
    expect(model()?.project?.documents.map((document) => document.id)).toEqual([second.id]);
    // The deleted active document falls back to the remaining chapter.
    expect(view().editor.activeDocument?.id).toBe(second.id);
    expect(() => getByRole(container, "button", { name: "Delete Opening" })).toThrow();
  });

  it("wires deletion failures to the row's inline error surface", async () => {
    stubBootstrapReads();
    vi.mocked(api.deleteDocument).mockRejectedValue(
      new Error("Document is referenced by a snapshot."),
    );
    const { container, view } = await mountNavigatorPage();

    act(() => fireEvent.click(getByRole(container, "button", { name: "Delete Opening" })));
    act(() => fireEvent.click(getByRole(container, "button", { name: "Confirm delete Opening" })));
    await flushEffects();

    expect(view().navigator.rowCommands?.deletionErrorFor(opening.id)).toBe(
      "Document is referenced by a snapshot.",
    );
    const alert = container.querySelector(".document-row__confirm .document-row__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("Document is referenced by a snapshot.");
  });

  it("wires placement end to end: choosing another volume patches the shell row", async () => {
    stubBootstrapReads();
    vi.mocked(api.moveChapterToVolume).mockResolvedValue({
      ...opening,
      volume_id: volumeTwo.id,
      position: 3,
      updated_at: "2026-09-06T00:00:00Z",
    });
    const { container, model } = await mountNavigatorPage();

    const select = getByRole(container, "combobox", { name: "Place Opening in volume" });
    act(() => fireEvent.change(select, { target: { value: volumeTwo.id } }));
    await flushEffects();

    expect(api.moveChapterToVolume).toHaveBeenCalledWith(project.id, opening.id, volumeTwo.id);
    const placed = model()?.project?.documents.find((document) => document.id === opening.id);
    expect(placed).toMatchObject({ volume_id: volumeTwo.id, position: 3 });
  });

  it("wires placement failures to the row's inline error surface", async () => {
    stubBootstrapReads();
    vi.mocked(api.moveChapterToVolume).mockRejectedValue(
      new Error("That volume is full: volume_chapters limit is 2000."),
    );
    const { container, view } = await mountNavigatorPage();

    const select = getByRole(container, "combobox", { name: "Place Opening in volume" });
    act(() => fireEvent.change(select, { target: { value: volumeTwo.id } }));
    await flushEffects();

    expect(view().navigator.rowCommands?.placementErrorFor(opening.id)).toBe(
      "That volume is full: volume_chapters limit is 2000.",
    );
    const alert = container.querySelector(".document-row__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe("That volume is full: volume_chapters limit is 2000.");
    const kept = view().project.documents.find((document) => document.id === opening.id);
    expect(kept).toMatchObject({ volume_id: volumeOne.id, position: opening.position });
  });
});
