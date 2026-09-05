import { fireEvent, getByRole } from "@testing-library/dom";
import { act } from "react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness, flushEffects } from "@/test/harness";
import { StudioInspectorPanels } from "../StudioInspectorPanels";
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
      reviews: vi.fn<typeof actual.api.reviews>(),
      exports: vi.fn<typeof actual.api.exports>(),
      saveLoreStatus: vi.fn<typeof actual.api.saveLoreStatus>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("Studio page Lore status authority", () => {
  it("uses the saved shell status without replacing or refetching the accepted body", async () => {
    const character = chapter("lore-status-character", {
      kind: "character",
      lore_status: "draft",
      content_markdown: "Mara keeps the harbor light burning.",
    });
    const project = projectWith([summarizeDocument(character)]);
    vi.mocked(api.project).mockResolvedValue(project);
    vi.mocked(api.document).mockResolvedValue(character);
    vi.mocked(api.providers).mockResolvedValue({ providers: [] });
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [], next_cursor: null });
    vi.mocked(api.revisions).mockResolvedValue({ revisions: [], next_cursor: null });
    vi.mocked(api.reviews).mockResolvedValue({ reviews: [] });
    vi.mocked(api.exports).mockResolvedValue({ exports: [] });
    vi.mocked(api.saveLoreStatus)
      .mockResolvedValueOnce({ lore_status: "stable" })
      .mockResolvedValueOnce({ lore_status: "draft" });

    const route = resolveStudioRoute(project.id, "characters", "");
    let current: ReturnType<typeof useStudioPageModel> | undefined;
    function Probe() {
      current = useStudioPageModel(project.id, route, useNavigate());
      const inspector = current.viewProps?.inspector;
      return inspector ? (
        <StudioInspectorPanels
          inspector={inspector.inspector}
          model={inspector.model}
          pending={inspector.pending}
          tabId={(tab) => `tab-${tab}`}
          panelId={(tab) => `panel-${tab}`}
        />
      ) : null;
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
    const acceptedBody = view().editor.activeDocument;
    expect(acceptedBody).toBe(character);
    const select = getByRole(container, "combobox", { name: "Lore status" });
    const save = () => getByRole(container, "button", { name: "Save status" }) as HTMLButtonElement;
    expect(save().disabled).toBe(true);

    act(() => fireEvent.change(select, { target: { value: "stable" } }));
    await act(async () => fireEvent.click(save()));

    expect(api.saveLoreStatus).toHaveBeenLastCalledWith(project.id, character.id, "stable");
    expect(current?.project?.documents[0]?.lore_status).toBe("stable");
    expect(view().editor.activeDocument).toBe(acceptedBody);
    expect(view().editor.activeDocument?.current_revision_id).toBe(character.current_revision_id);
    expect(view().editor.draft).toBe(character.content_markdown);
    expect(api.document).toHaveBeenCalledOnce();
    expect(view().inspector.model.loreStatus?.savedStatus).toBe("stable");
    expect(save().disabled).toBe(true);

    act(() => fireEvent.change(select, { target: { value: "draft" } }));
    expect(save().disabled).toBe(false);
    await act(async () => fireEvent.click(save()));

    expect(api.saveLoreStatus).toHaveBeenCalledTimes(2);
    expect(api.saveLoreStatus).toHaveBeenLastCalledWith(project.id, character.id, "draft");
    expect(view().inspector.model.loreStatus?.savedStatus).toBe("draft");
    expect(save().disabled).toBe(true);
    expect(view().editor.activeDocument).toBe(acceptedBody);
    expect(view().editor.draft).toBe(character.content_markdown);
    expect(api.document).toHaveBeenCalledOnce();
  });
});
