import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useLocation, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { StudioNavigator } from "../StudioNavigator";
import { resolveStudioRoute } from "../studioRouteState";
import { summarizeDocument } from "./projectState";
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
      search: vi.fn<typeof actual.api.search>(),
    },
  };
});

const harness = createMountHarness();
afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

const documents = [
  chapter("chapter-1", { title: "Opening", content_markdown: "willowquill chapter" }),
  chapter("character-1", {
    kind: "character",
    title: "Mira",
    content_markdown: "willowquill character",
    volume_id: null,
    lore_status: "draft",
  }),
  chapter("character-2", {
    kind: "character",
    title: "Ada",
    content_markdown: "willowquill Ada",
    volume_id: null,
    lore_status: "draft",
  }),
  chapter("outline-1", {
    kind: "outline",
    title: "Outline",
    content_markdown: "willowquill outline",
    volume_id: null,
  }),
  chapter("note-1", {
    kind: "note",
    title: "Notes",
    content_markdown: "willowquill note",
    volume_id: null,
  }),
  chapter("world-1", {
    kind: "world",
    title: "Harbor",
    content_markdown: "willowquill world",
    volume_id: null,
    lore_status: "draft",
  }),
];
const project = projectWith(documents.map(summarizeDocument), { volumes: [volume("volume-1", 0)] });

async function mountSearch(section: string, targetId: string, inspector = "copilot") {
  const target = documents.find((document) => document.id === targetId);
  if (!target) throw new Error("Missing target fixture.");
  vi.mocked(api.project).mockResolvedValue(project);
  vi.mocked(api.document).mockImplementation(async (_projectId, id) => {
    const document = documents.find((candidate) => candidate.id === id);
    if (!document) throw new Error("Unexpected document read.");
    return document;
  });
  vi.mocked(api.providers).mockResolvedValue({ providers: [] });
  vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
  vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
  vi.mocked(api.search).mockResolvedValue({
    results: [
      {
        document_id: target.id,
        title: target.title,
        excerpt: target.content_markdown,
        match_term: "willowquill",
      },
    ],
    total: 1,
    next_offset: null,
  });
  let current: ReturnType<typeof useStudioPageModel> | undefined;
  let currentPath = "";
  function Probe() {
    const location = useLocation();
    currentPath = `${location.pathname}${location.search}`;
    const route = resolveStudioRoute(
      project.id,
      location.pathname.split("/").at(-1),
      location.search,
    );
    current = useStudioPageModel(project.id, route, useNavigate());
    return current.viewProps ? <StudioNavigator {...current.viewProps.navigator} /> : null;
  }
  const { container } = harness.mount(
    <MemoryRouter
      initialEntries={[
        `/projects/${project.id}/${section}${inspector === "copilot" ? "" : `?inspector=${inspector}`}`,
      ]}
    >
      <Probe />
    </MemoryRouter>,
  );
  await flushEffects();
  const input = getByRole(container, "textbox", { name: "Search project" });
  await act(() => fireEvent.change(input, { target: { value: "willowquill" } }));
  const form = input.closest("form");
  if (!form) throw new Error("Expected search form.");
  await act(async () => {
    fireEvent.submit(form);
  });
  await act(() => fireEvent.click(getByRole(container, "button", { name: `Open ${target.title}` })));
  await flushEffects();
  if (!current?.viewProps) throw new Error("Expected loaded Studio.");
  return { view: current.viewProps, target, currentPath };
}

describe("project search result selection through the Studio page model", () => {
  it.each([
    ["characters", "character-2", "characters"],
    ["outline", "chapter-1", "manuscript"],
    ["characters", "chapter-1", "manuscript"],
    ["world", "chapter-1", "manuscript"],
    ["manuscript", "character-2", "manuscript"],
    ["outline", "character-2", "manuscript"],
    ["characters", "world-1", "manuscript"],
    ["world", "outline-1", "manuscript"],
    ["characters", "note-1", "manuscript"],
  ])("opens %s search result %s", async (section, targetId, expectedSection) => {
    const { view, target, currentPath } = await mountSearch(section, targetId);
    expect(currentPath).toBe(`/projects/${project.id}/${expectedSection}`);
    expect(view.editor.activeDocument?.id).toBe(target.id);
    expect(view.editor.draft).toBe(target.content_markdown);
    expect(view.navigator.activeId).toBe(target.id);
    expect(view.editor.reveal).toMatchObject({ documentId: target.id, term: "willowquill" });
  });

  it("retains the local inspector when a search result requires another section", async () => {
    const { view, target, currentPath } = await mountSearch("characters", "chapter-1", "jobs");
    expect(currentPath).toBe(`/projects/${project.id}/manuscript?inspector=jobs`);
    expect(view.inspector.inspector).toBe("jobs");
    expect(view.editor.draft).toBe(target.content_markdown);
    expect(view.editor.reveal).toMatchObject({ documentId: target.id, term: "willowquill" });
  });
});
