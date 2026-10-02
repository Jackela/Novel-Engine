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
      createVolume: vi.fn<typeof actual.api.createVolume>(),
      renameVolume: vi.fn<typeof actual.api.renameVolume>(),
      deleteVolume: vi.fn<typeof actual.api.deleteVolume>(),
      reorderVolumes: vi.fn<typeof actual.api.reorderVolumes>(),
      moveChapterToVolume: vi.fn<typeof actual.api.moveChapterToVolume>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

const defaultVolume = volume("volume-1", 1, { title: "Default Volume" });
const actTwo = volume("volume-2", 2, { title: "Act Two" });
const opening = chapter("doc-1", { title: "Opening", position: 1 });
const second = chapter("doc-2", { title: "Second", position: 2 });
const project = projectWith([opening, second], { volumes: [defaultVolume] });
const twoVolumeProject = projectWith([opening, { ...second, volume_id: actTwo.id }], {
  volumes: [defaultVolume, actTwo],
});

function stubBootstrapReads(shell = project): void {
  vi.mocked(api.project).mockResolvedValue(shell);
  vi.mocked(api.document).mockImplementation(async (_projectId, documentId) =>
    documentId === second.id ? second : opening,
  );
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.reviews).mockResolvedValue({ reviews: [], next_cursor: null });
  vi.mocked(api.exports).mockResolvedValue({ exports: [], next_cursor: null });
}

async function mountNavigatorPage(shell = project) {
  stubBootstrapReads(shell);
  const route = resolveStudioRoute(shell.id, "manuscript", "");
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  function Probe() {
    current = useStudioPageModel(shell.id, route, useNavigate());
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

function control(container: HTMLElement, label: string): HTMLElement {
  const element = container.querySelector<HTMLElement>(`[aria-label="${label}"]`);
  if (element === null) throw new Error(`Expected control: ${label}`);
  return element;
}

function click(element: HTMLElement): void {
  act(() => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

describe("Studio page model volume commands", () => {
  it("creates a volume and makes its chapter placement affordance reachable", async () => {
    vi.mocked(api.createVolume).mockResolvedValue(actTwo);
    vi.mocked(api.moveChapterToVolume).mockResolvedValue({
      ...opening,
      volume_id: actTwo.id,
      position: 1,
      updated_at: "2026-09-06T00:00:00Z",
    });
    const { container, model } = await mountNavigatorPage();

    click(control(container, "Add volume"));
    act(() => {
      fireEvent.change(control(container, "Volume title"), { target: { value: "Act Two" } });
    });
    click(control(container, "Create volume"));
    await flushEffects();

    expect(api.createVolume).toHaveBeenCalledWith(project.id, "Act Two");
    expect(model()?.project?.volumes.map((volume) => volume.title)).toEqual([
      "Default Volume",
      "Act Two",
    ]);
    expect(control(container, "Add volume")).toBeDefined();
    expect(container.querySelector('input[aria-label="Volume title"]')).toBeNull();

    // With a real second volume the row-action placement select renders, and
    // the existing moveDocument client path places the chapter end to end.
    const select = getByRole(container, "combobox", {
      name: "Place Opening in volume",
    }) as HTMLSelectElement;
    expect(Array.from(select.options).map((option) => option.value)).toEqual(["", actTwo.id]);
    void act(() => fireEvent.change(select, { target: { value: actTwo.id } }));
    await flushEffects();

    expect(api.moveChapterToVolume).toHaveBeenCalledWith(project.id, opening.id, actTwo.id);
    expect(
      model()?.project?.documents.find((document) => document.id === opening.id),
    ).toMatchObject({ volume_id: actTwo.id, position: 1 });
  });

  it("renames a volume through the shell and keeps the input error surface", async () => {
    vi.mocked(api.renameVolume).mockResolvedValue({
      ...defaultVolume,
      title: "Book One",
      updated_at: "2026-09-06T00:00:00Z",
    });
    const { container, model } = await mountNavigatorPage();

    click(control(container, "Rename Default Volume"));
    act(() => {
      fireEvent.change(control(container, "New title for Default Volume"), {
        target: { value: "Book One" },
      });
    });
    click(control(container, "Save name for Default Volume"));
    await flushEffects();

    expect(api.renameVolume).toHaveBeenCalledWith(project.id, defaultVolume.id, "Book One");
    expect(model()?.project?.volumes[0]?.title).toBe("Book One");
    expect(container.querySelector('input[aria-label="New title for Book One"]')).toBeNull();
    expect(control(container, "Rename Book One")).toBeDefined();
  });

  it("reorders volumes through the whole-set API and applies the server order", async () => {
    vi.mocked(api.reorderVolumes).mockResolvedValue({
      volumes: [
        { ...actTwo, position: 1 },
        { ...defaultVolume, position: 2 },
      ],
    });
    const { container, model } = await mountNavigatorPage(twoVolumeProject);

    click(control(container, "Move Act Two up"));
    await flushEffects();

    expect(api.reorderVolumes).toHaveBeenCalledWith(project.id, [actTwo.id, defaultVolume.id]);
    expect(model()?.project?.volumes.map((volume) => volume.id)).toEqual([
      actTwo.id,
      defaultVolume.id,
    ]);
  });

  it("deletes a volume and merges its chapters into the preceding volume", async () => {
    vi.mocked(api.deleteVolume).mockResolvedValue(undefined);
    const { container, model } = await mountNavigatorPage(twoVolumeProject);

    click(control(container, "Delete Act Two"));
    click(control(container, "Confirm delete Act Two"));
    await flushEffects();

    expect(api.deleteVolume).toHaveBeenCalledWith(project.id, actTwo.id);
    expect(model()?.project?.volumes.map((volume) => volume.id)).toEqual([defaultVolume.id]);
    expect(model()?.project?.documents.find((document) => document.id === second.id)).toMatchObject(
      {
        volume_id: defaultVolume.id,
      },
    );
    // The row survives under the merged predecessor, in reading order.
    expect(container.querySelectorAll(".volume-group")).toHaveLength(1);
    const rowLabels = Array.from(container.querySelectorAll(".document-row")).map((row) =>
      row.getAttribute("aria-label"),
    );
    expect(rowLabels).toEqual(["Opening", "Second"]);
  });

  it("keeps the volume and surfaces the server's refusal when deletion is rejected", async () => {
    const refusal =
      "A project must keep at least one volume; create another before deleting this one.";
    vi.mocked(api.deleteVolume).mockRejectedValue(new Error(refusal));
    const { container, model } = await mountNavigatorPage();

    click(control(container, "Delete Default Volume"));
    click(control(container, "Confirm delete Default Volume"));
    await flushEffects();

    expect(api.deleteVolume).toHaveBeenCalledWith(project.id, defaultVolume.id);
    expect(model()?.project?.volumes.map((volume) => volume.id)).toEqual([defaultVolume.id]);
    const alert = container.querySelector(".volume-group__confirm .volume-group__error");
    expect(alert?.getAttribute("role")).toBe("alert");
    expect(alert?.textContent).toBe(refusal);
  });
});
