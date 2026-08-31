import { act, type FormEvent } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Project } from "@/app/types/studio";
import { chapter, projectWith, volume } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioNavigator } from "./StudioNavigator";

const harness = createMountHarness();

function render(element: Parameters<typeof harness.mount>[0]): HTMLDivElement {
  return harness.mount(element).container;
}

function click(element: Element | null): void {
  if (!(element instanceof HTMLElement)) {
    throw new Error("Expected a clickable element.");
  }
  act(() => {
    element.click();
  });
}

afterEach(() => {
  harness.cleanup();
});

const baseDocument = chapter("doc-1", {
  title: "Opening",
  position: 1,
  current_revision_id: "revision-abcdefghi",
  content_markdown: "# Opening",
  revision_source: "author",
  word_count: 42,
});

const secondDocument = {
  ...baseDocument,
  id: "doc-2",
  title: "Second",
  position: 2,
  current_revision_id: "revision-second",
  word_count: 12,
};

const baseProject = projectWith([baseDocument, secondDocument]);

describe("StudioNavigator", () => {
  it("keeps navigation callbacks scoped to section, search, and document actions", () => {
    const callbacks = {
      searchChange: vi.fn(),
      searchSubmit: vi.fn((event: FormEvent) => event.preventDefault()),
      navigateSection: vi.fn(),
      selectDocument: vi.fn(),
      createDocument: vi.fn(),
      moveDocument: vi.fn(),
    };

    const container = render(
      <StudioNavigator
        project={baseProject}
        section="manuscript"
        activeId="doc-1"
        search="harbor"
        isSearching={false}
        searchResults={[{ document_id: "doc-1", title: "Opening", excerpt: "Harbor" }]}
        onSearchChange={callbacks.searchChange}
        onSearchSubmit={callbacks.searchSubmit}
        onNavigateSection={callbacks.navigateSection}
        onSelectDocument={callbacks.selectDocument}
        onCreateDocument={callbacks.createDocument}
        onMoveDocument={callbacks.moveDocument}
      />,
    );

    expect(container.querySelector("summary.studio-nav__summary")).not.toBeNull();
    expect(container.querySelector("summary")?.textContent).toContain("Project navigation");
    expect(container.querySelector("summary")?.hasAttribute("aria-label")).toBe(false);
    expect(container.querySelector('button[aria-label="Add Manuscript"]')).not.toBeNull();
    expect(container.querySelector('button[aria-label="Move Second down"]')).not.toBeNull();

    click(Array.from(container.querySelectorAll(".studio-nav__sections button"))[1]);
    click(container.querySelector(".studio-nav__search-results button"));
    click(container.querySelector(".studio-nav__document-group header button"));
    click(container.querySelector(".document-row__order button:last-child"));
    act(() => {
      container.querySelector("form")?.dispatchEvent(new Event("submit", { bubbles: true }));
    });

    expect(callbacks.navigateSection).toHaveBeenCalledWith("outline");
    expect(callbacks.selectDocument).toHaveBeenCalledWith("doc-1");
    expect(callbacks.createDocument).toHaveBeenCalledWith("chapter");
    expect(callbacks.moveDocument).toHaveBeenCalledWith("doc-1", 1);
    expect(callbacks.searchSubmit).toHaveBeenCalledTimes(1);
  });

  it("groups manuscript chapters under volume headers in reading order", () => {
    const firstVolume = volume("volume-1", 1, { title: "Default Volume" });
    const bookTwo = volume("volume-2", 2, { title: "Book Two" });
    const chapterTwo = {
      ...baseDocument,
      id: "doc-2",
      title: "Second",
      position: 2,
      volume_id: "volume-2",
    };
    const groupedProject: Project = {
      ...baseProject,
      documents: [baseDocument, chapterTwo],
      volumes: [firstVolume, bookTwo],
    };

    const container = render(
      <StudioNavigator
        project={groupedProject}
        section="manuscript"
        activeId="doc-1"
        search=""
        isSearching={false}
        searchResults={[]}
        onSearchChange={() => undefined}
        onSearchSubmit={(event) => event.preventDefault()}
        onNavigateSection={() => undefined}
        onSelectDocument={() => undefined}
        onCreateDocument={() => undefined}
        onMoveDocument={() => undefined}
      />,
    );

    const headers = Array.from(container.querySelectorAll(".studio-nav__volume-header"));
    expect(headers.map((header) => header.textContent)).toEqual(["Default Volume", "Book Two"]);

    // Chapters land under their owning volume; the seed stays in the default
    // volume and the second chapter follows Book Two's header.
    const groups = Array.from(container.querySelectorAll(".volume-group"));
    expect(groups[0]?.textContent).toContain("Opening");
    expect(groups[0]?.textContent).not.toContain("Second");
    expect(groups[1]?.textContent).toContain("Second");
  });

  it("shows the in-volume ordinal and only renders a linked beat title (#376)", () => {
    const linkedChapter = {
      ...baseDocument,
      id: "doc-2",
      title: "Second",
      position: 2,
      beat_ref: "The Harbor Bell",
    };
    const unlinkedChapter = {
      ...baseDocument,
      id: "doc-3",
      title: "Third",
      position: 3,
      beat_ref: null,
    };
    const container = render(
      <StudioNavigator
        project={{
          ...baseProject,
          documents: [baseDocument, linkedChapter, unlinkedChapter],
        }}
        section="manuscript"
        activeId="doc-1"
        search=""
        isSearching={false}
        searchResults={[]}
        onSearchChange={() => undefined}
        onSearchSubmit={(event) => event.preventDefault()}
        onNavigateSection={() => undefined}
        onSelectDocument={() => undefined}
        onCreateDocument={() => undefined}
        onMoveDocument={() => undefined}
      />,
    );

    const rows = Array.from(container.querySelectorAll(".document-row"));
    expect(rows).toHaveLength(3);

    // Ordinals come from document.position (the in-volume order), not titles.
    const ordinals = rows.map((row) => row.querySelector(".document-row__ordinal")?.textContent);
    expect(ordinals).toEqual(["1", "2", "3"]);

    // beat_ref is a title soft link: rendered only when non-null (also covers
    // the undefined branch — the first chapter carries no beat_ref at all).
    expect(rows[0]?.querySelector(".document-row__beat")).toBeNull();
    expect(rows[1]?.querySelector(".document-row__beat")?.textContent).toBe("The Harbor Bell");
    expect(rows[2]?.querySelector(".document-row__beat")).toBeNull();
  });

  it("renders lore lifecycle status badges on lore rows only (#444)", () => {
    const stableCharacter = {
      ...baseDocument,
      id: "doc-2",
      kind: "character" as const,
      title: "Mara",
      position: 1,
      lore_status: "stable" as const,
    };
    const draftWorld = {
      ...baseDocument,
      id: "doc-3",
      kind: "world" as const,
      title: "Sable Reaches",
      position: 2,
      lore_status: "draft" as const,
    };
    const container = render(
      <StudioNavigator
        project={projectWith([baseDocument, stableCharacter, draftWorld])}
        section="manuscript"
        activeId="doc-1"
        search=""
        isSearching={false}
        searchResults={[]}
        onSearchChange={() => undefined}
        onSearchSubmit={(event) => event.preventDefault()}
        onNavigateSection={() => undefined}
        onSelectDocument={() => undefined}
        onCreateDocument={() => undefined}
        onMoveDocument={() => undefined}
      />,
    );

    const rows = Array.from(container.querySelectorAll(".document-row"));
    expect(rows).toHaveLength(3);

    // Badges ride only on lore rows and carry the closed status vocabulary.
    expect(rows[0]?.querySelector(".document-row__lore-status")).toBeNull();
    const stableBadge = rows[1]?.querySelector(".document-row__lore-status");
    expect(stableBadge?.textContent).toBe("stable");
    expect(stableBadge?.className).toContain("document-row__lore-status--stable");
    const draftBadge = rows[2]?.querySelector(".document-row__lore-status");
    expect(draftBadge?.textContent).toBe("draft");
    expect(draftBadge?.className).toContain("document-row__lore-status--draft");

    // Badges are presentational; the row name carries the status instead.
    expect(rows[1]?.getAttribute("aria-label")).toBe("Mara — stable");
    expect(rows[2]?.getAttribute("aria-label")).toBe("Sable Reaches — draft");
  });
});
