import { fireEvent, getByRole } from "@testing-library/dom";
import { act, useState } from "react";
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

async function render(element: React.ReactElement): Promise<HTMLDivElement> {
  const { container } = harness.mount(element);
  await flushEffects();
  return container;
}

/**
 * The command owner's committed lifecycle: pending while the request runs,
 * then the successful command's normalized value becomes the stored reference
 * (#466) — which is exactly what disables the initiating control.
 */
function SuccessfulBeatHarness({
  save,
  initialBeatRef,
}: {
  save: ReturnType<typeof deferred<void>>;
  initialBeatRef: string | null;
}) {
  const [isSaving, setIsSaving] = useState(false);
  const [beatRef, setBeatRef] = useState<string | null>(initialBeatRef);
  return (
    <StudioBeatPanel
      projectId="project-1"
      documentId="doc-1"
      beatRef={beatRef}
      isSaving={isSaving}
      onLink={async (beat) => {
        setIsSaving(true);
        await save.promise;
        setBeatRef(beat);
        setIsSaving(false);
      }}
    />
  );
}

describe("StudioBeatPanel (#466)", () => {
  it("moves focus to the catalog select when a successful link disables the submit button", async () => {
    const save = deferred<void>();
    const container = await render(<SuccessfulBeatHarness initialBeatRef={null} save={save} />);
    const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    void act(() => fireEvent.change(select, { target: { value: "The Harbor" } }));

    linkButton.focus();
    void act(() => fireEvent.submit(linkButton));
    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    // Success keeps the submit command disabled (`requested === beatRef`),
    // so the select is the semantic landing zone.
    expect(getByRole(container, "button", { name: "Link beat" })).toBeDisabled();
    expect(document.activeElement).toBe(select);
  });

  it("moves focus to the catalog select when a successful clear disables the clear button", async () => {
    const save = deferred<void>();
    const container = await render(
      <SuccessfulBeatHarness initialBeatRef="The Harbor" save={save} />,
    );
    const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    const clearButton = getByRole(container, "button", { name: "Clear" });

    clearButton.focus();
    await act(async () => {
      fireEvent.click(clearButton);
      await Promise.resolve();
    });
    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(getByRole(container, "button", { name: "Clear" })).toBeDisabled();
    expect(document.activeElement).toBe(select);
  });

  it("does not override focus the author moved during a beat save", async () => {
    const save = deferred<void>();
    const container = await render(
      <StudioBeatPanel
        projectId="project-1"
        documentId="doc-1"
        beatRef={null}
        onLink={() => save.promise}
      />,
    );
    const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    void act(() => fireEvent.change(select, { target: { value: "The Harbor" } }));
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    const otherButton = document.createElement("button");
    document.body.appendChild(otherButton);
    linkButton.focus();

    void act(() => fireEvent.submit(linkButton));
    otherButton.focus();
    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(document.activeElement).toBe(otherButton);
    otherButton.remove();
  });

  it("does not steal focus when document A settles after document B becomes active", async () => {
    const save = deferred<void>();
    const content = (documentId: string) => (
      <StudioBeatPanel
        projectId="project-1"
        documentId={documentId}
        beatRef={null}
        onLink={() => save.promise}
      />
    );
    const { container, root } = harness.mount(content("doc-1"));
    await flushEffects();
    const selectA = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    void act(() => fireEvent.change(selectA, { target: { value: "The Harbor" } }));
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    linkButton.focus();
    void act(() => fireEvent.submit(linkButton));

    // The same persistent owner now carries document B; its keyed form
    // remounts, and the author's focus belongs to the new document.
    act(() => root.render(content("doc-2")));
    await flushEffects();
    const selectB = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    selectB.focus();

    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(document.activeElement).toBe(selectB);
  });

  it("keeps body focus when document A settles after the switch, with nothing focused", async () => {
    const save = deferred<void>();
    const content = (documentId: string) => (
      <StudioBeatPanel
        projectId="project-1"
        documentId={documentId}
        beatRef={null}
        onLink={() => save.promise}
      />
    );
    const { container, root } = harness.mount(content("doc-1"));
    await flushEffects();
    const selectA = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    void act(() => fireEvent.change(selectA, { target: { value: "The Harbor" } }));
    const linkButton = getByRole(container, "button", { name: "Link beat" });
    linkButton.focus();
    void act(() => fireEvent.submit(linkButton));

    // The Safari click-without-focus shape: the keyed remount for document B
    // leaves focus on body, so only the same-document guard stops the settled
    // command from programmatically focusing the new document's select.
    act(() => root.render(content("doc-2")));
    await flushEffects();
    expect(document.activeElement).toBe(document.body);

    await act(async () => {
      save.resolve(undefined);
      await save.promise;
    });

    expect(document.activeElement).toBe(document.body);
  });

  it("announces failures assertively like every other error surface", async () => {
    const container = await render(
      <StudioBeatPanel
        projectId="project-1"
        documentId="doc-1"
        beatRef={null}
        error="Unable to update the chapter beat."
        onLink={vi.fn()}
      />,
    );
    const alert = getByRole(container, "alert");
    expect(alert.getAttribute("aria-live")).toBe("assertive");
  });

  it("links the selected candidate by its title (DR-043)", async () => {
    const onLink = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    const container = await render(
      <StudioBeatPanel projectId="project-1" documentId="doc-1" beatRef={null} onLink={onLink} />,
    );

    const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    expect(select.disabled).toBe(false);
    void act(() => fireEvent.change(select, { target: { value: "The Storm" } }));
    await act(async () => {
      getByRole(container, "button", { name: "Link beat" }).click();
      await Promise.resolve();
    });

    expect(onLink).toHaveBeenCalledWith("The Storm");
    expect(api.chapterBeat).toHaveBeenCalledWith("project-1", "doc-1", expect.anything());
  });

  it("keeps a still-stored reference selectable when the outline no longer holds it (DR-043)", async () => {
    const container = await render(
      <StudioBeatPanel
        projectId="project-1"
        documentId="doc-1"
        beatRef="The Vanished"
        onLink={vi.fn()}
      />,
    );

    const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    expect(select.value).toBe("The Vanished");
    // The stored reference is the option's identity, not a silent blank.
    expect(Array.from(select.options).map((option) => option.value)).toEqual([
      "",
      "The Vanished",
      "The Harbor",
      "The Storm",
    ]);
  });

  it("names the authoritative outline when several outlines exist (DR-043)", async () => {
    vi.mocked(api.chapterBeat).mockResolvedValue({
      beat: null,
      candidates: [{ title: "The Tempest" }],
      outline: { document_id: "outline-2", title: "Alternate outline", outline_count: 2 },
    });
    const container = await render(
      <StudioBeatPanel projectId="project-1" documentId="doc-1" beatRef={null} onLink={vi.fn()} />,
    );

    expect(container).toHaveTextContent(
      "This project has 2 outlines; beats come from “Alternate outline”.",
    );
  });

  it("surfaces a failed candidate read instead of pretending the outline is empty (DR-043)", async () => {
    vi.mocked(api.chapterBeat).mockRejectedValue("offline");
    const container = await render(
      <StudioBeatPanel projectId="project-1" documentId="doc-1" beatRef={null} onLink={vi.fn()} />,
    );

    expect(getByRole(container, "alert")).toHaveTextContent("Unable to load the outline beats.");
  });

  it("refreshes the catalog through the manual refresh command (DR-043)", async () => {
    const container = await render(
      <StudioBeatPanel projectId="project-1" documentId="doc-1" beatRef={null} onLink={vi.fn()} />,
    );
    expect(api.chapterBeat).toHaveBeenCalledTimes(1);

    vi.mocked(api.chapterBeat).mockResolvedValue({
      beat: null,
      candidates: [{ title: "The Tempest" }],
      outline: { document_id: "outline-1", title: "Outline", outline_count: 1 },
    });
    await act(async () => {
      getByRole(container, "button", { name: "Refresh beats" }).click();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(api.chapterBeat).toHaveBeenCalledTimes(2);
    const select = getByRole(container, "combobox", { name: "Beat title" }) as HTMLSelectElement;
    expect(Array.from(select.options).map((option) => option.value)).toEqual(["", "The Tempest"]);
  });
});
