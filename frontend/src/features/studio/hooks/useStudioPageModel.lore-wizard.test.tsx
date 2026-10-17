import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/app/api";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, deferred, flushEffects } from "@/test/harness";
import { StudioInspectorPanels } from "../StudioInspectorPanels";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
import { candidate, loreJob } from "./useLorebookWizardTestHarness";
import { useStudioPageModel } from "./useStudioPageModel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      project: vi.fn(),
      document: vi.fn(),
      providers: vi.fn(),
      jobs: vi.fn(),
      revisions: vi.fn(),
      extractLore: vi.fn(),
      createDocument: vi.fn(),
      saveDocumentAliases: vi.fn(),
      saveDocument: vi.fn(),
    },
  };
});
const harness = createMountHarness();
afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

it("publishes a created Lore entry before aliases settle without replacing the active draft", async () => {
  const manuscript = chapter("chapter-1", { content_markdown: "Accepted text" });
  const lore = chapter("mira", {
    kind: "character",
    lore_status: "draft",
    title: "Mira",
    content_markdown: "Keeps the ledger.",
  });
  const project = projectWith([summarizeDocument(manuscript)]);
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.document).mockResolvedValue(manuscript);
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.extractLore).mockResolvedValue(
    loreJob([candidate("character", "Mira", ["Clerk"])]),
  );
  vi.mocked(api.createDocument).mockResolvedValue(lore);
  const aliases = deferred<Awaited<ReturnType<typeof api.saveDocumentAliases>>>();
  vi.mocked(api.saveDocumentAliases).mockReturnValue(aliases.promise);
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  const route = resolveStudioRoute(project.id, "manuscript", "?inspector=lore");
  function Probe() {
    current = useStudioPageModel(project.id, route, useNavigate());
    const inspector = current.viewProps?.inspector;
    return inspector ? (
      <StudioInspectorPanels
        {...inspector}
        tabId={(tab) => `tab-${tab}`}
        panelId={(tab) => `panel-${tab}`}
      />
    ) : null;
  }
  const { container } = harness.mount(
    <MemoryRouter>
      <Probe />
    </MemoryRouter>,
  );
  await flushEffects();
  const view = () => {
    if (!current?.viewProps) throw new Error("Expected loaded Studio.");
    return current.viewProps;
  };
  act(() => {
    view().editor.onDraftChange("Unfinished local paragraph");
  });
  act(() => {
    fireEvent.change(getByRole(container, "textbox", { name: "Paste a draft segment" }), {
      target: { value: "Mira arrived." },
    });
    fireEvent.submit(getByRole(container, "form", { name: "Paste a draft segment" }));
  });
  await flushEffects();
  act(() => {
    fireEvent.click(getByRole(container, "button", { name: "Add 1 selected to lorebook" }));
  });
  await flushEffects();
  expect(current?.project?.documents.map((document) => document.id)).toEqual([
    manuscript.id,
    lore.id,
  ]);
  act(() => {
    view().inspector.model.lore.onDocumentCreated?.(lore);
    view().inspector.model.lore.onDocumentCreated?.({
      ...lore,
      id: "foreign",
      project_id: "other-project",
    });
  });
  expect(current?.project?.documents.map((document) => document.id)).toEqual([
    manuscript.id,
    lore.id,
  ]);
  expect(view().editor.draft).toBe("Unfinished local paragraph");
  expect(view().editor.activeDocument).toBe(manuscript);
  expect(getByRole(container, "button", { name: "Adding entries…" })).toBeDisabled();
  expect(api.project).toHaveBeenCalledTimes(1);
  expect(api.document).toHaveBeenCalledTimes(1);
  await act(async () => {
    aliases.resolve({ aliases: ["Clerk"] });
  });
});

it("ignores a departing project's late creation notification", async () => {
  const first = projectWith([], { id: "project-1" });
  const second = projectWith([], { id: "project-2" });
  vi.mocked(api.project).mockImplementation(async (projectId) =>
    projectId === first.id ? first : second,
  );
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  function Probe({ projectId }: { projectId: string }) {
    current = useStudioPageModel(
      projectId,
      resolveStudioRoute(projectId, "manuscript", "?inspector=lore"),
      useNavigate(),
    );
    return null;
  }
  const mounted = harness.mount(
    <MemoryRouter>
      <Probe projectId={first.id} />
    </MemoryRouter>,
  );
  await flushEffects();
  const lateCreation = current?.viewProps?.inspector.model.lore.onDocumentCreated;
  expect(lateCreation).toBeTypeOf("function");
  act(() => {
    mounted.root.render(
      <MemoryRouter>
        <Probe projectId={second.id} />
      </MemoryRouter>,
    );
  });
  await flushEffects();
  act(() => {
    lateCreation?.(chapter("mira", { kind: "character", project_id: first.id }));
  });
  expect(current?.project?.id).toBe(second.id);
  expect(current?.project?.documents).toEqual([]);
});
