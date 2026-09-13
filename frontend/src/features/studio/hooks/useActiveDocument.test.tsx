import { act } from "react";
import { afterEach, describe, expect, it } from "vitest";

import type { DocumentSummary, Project } from "@/app/types/studio";

import { chapter, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useActiveDocument } from "./useActiveDocument";

interface HookArgs {
  readonly project: Project | null;
  readonly section: string;
  readonly activeId: string | null;
}

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
});

const chapterOne = chapter("chapter-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  content_markdown: "Chapter content",
  revision_source: "author",
  word_count: 2,
});
const outline = {
  ...chapterOne,
  id: "outline-1",
  kind: "outline" as const,
  title: "Story Outline",
  position: 1,
};
const character = {
  ...chapterOne,
  id: "character-1",
  kind: "character" as const,
  title: "Ada",
  position: 2,
};
const project = projectWith([chapterOne, outline, character]);

function renderActiveDocument(initialArgs: HookArgs): {
  readonly result: () => DocumentSummary | null;
  readonly rerender: (args: HookArgs) => void;
} {
  let args = initialArgs;
  let current: DocumentSummary | null = null;

  function Wrapper(): null {
    current = useActiveDocument(args.project, args.section, args.activeId);
    return null;
  }

  const mounted = harness.mount(<Wrapper />);

  const render = () => mounted.root.render(<Wrapper />);

  return {
    result: () => current,
    rerender: (nextArgs) => {
      args = nextArgs;
      act(render);
    },
  };
}

describe("useActiveDocument", () => {
  it("returns the selected document when it belongs to the current section", () => {
    // Given / When
    const hook = renderActiveDocument({
      project,
      section: "manuscript",
      activeId: chapterOne.id,
    });

    // Then
    expect(hook.result()).toEqual(chapterOne);
  });

  it("returns the first document matching a scoped section", () => {
    // Given
    const hook = renderActiveDocument({
      project,
      section: "manuscript",
      activeId: chapterOne.id,
    });

    // When
    hook.rerender({ project, section: "characters", activeId: chapterOne.id });

    // Then
    expect(hook.result()).toEqual(character);
  });

  it("returns null when a scoped section has no matching document", () => {
    // Given / When
    const hook = renderActiveDocument({
      project: { ...project, documents: [chapterOne] },
      section: "world",
      activeId: chapterOne.id,
    });

    // Then
    expect(hook.result()).toBeNull();
  });
});
