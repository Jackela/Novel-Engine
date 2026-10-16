import { act, useState } from "react";

import type { Project, StudioDocument } from "@/app/types/studio";
import { createMountHarness, flushMicrotasks } from "@/test/harness";

import { useDocumentDraft } from "./useDocumentDraft";

/**
 * Mounts the Draft hook with its real project/error state and document
 * selection boundary. Reading before mount throws; cleanup unmounts every
 * mounted wrapper through the shared test harness.
 */
export function createDocumentDraftTestHarness(project: Project, initialDocument: StudioDocument) {
  const harness = createMountHarness();
  function renderDraft() {
    let body: StudioDocument | null = initialDocument;
    let selectedId: string | null = initialDocument.id;
    let current: { hook: ReturnType<typeof useDocumentDraft>; error: string | null } | undefined;
    function Wrapper() {
      const [, setProject] = useState<Project | null>(project);
      const [error, setError] = useState<string | null>(null);
      const hook = useDocumentDraft(
        body,
        project.id,
        setProject,
        setError,
        setError,
        setError,
        selectedId,
      );
      current = { hook, error };
      return null;
    }
    const { root } = harness.mount(<Wrapper />);
    return {
      result: () => {
        if (!current) throw new Error("Expected mounted draft.");
        return current;
      },
      select: async (document: StudioDocument | null, id: string | null = document?.id ?? null) => {
        body = document;
        selectedId = id;
        act(() => root.render(<Wrapper />));
        await flushMicrotasks();
      },
    };
  }

  return { renderDraft, cleanup: harness.cleanup };
}
