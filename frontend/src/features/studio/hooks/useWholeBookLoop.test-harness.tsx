import { act, useRef, useState } from "react";
import { afterEach, vi } from "vitest";

import { api } from "@/app/api";
import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import { chapter, job, projectWith } from "@/test/factories";
import { createMountHarness, deferred as sharedDeferred } from "@/test/harness";

import { useWholeBookLoop } from "./useWholeBookLoop";

export type HookResult = ReturnType<typeof useWholeBookLoop>;

export interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly accepted: StudioDocument[];
}

export interface Deferred<T> {
  readonly promise: Promise<T>;
  resolve: (value: T) => void;
}

const harness = createMountHarness();

export const deferred = sharedDeferred;

export const firstChapter = chapter("one", {
  title: "Chapter One",
  position: 0,
});
export const secondChapter = chapter("two", {
  title: "Chapter Two",
  position: 1,
});
export const baseProject = projectWith([firstChapter, secondChapter]);

export function proposalJobFor(documentId: string): StudioJob {
  return job({
    id: `job-${documentId}`,
    project_id: baseProject.id,
    document_id: documentId,
    operation: "generate" as const,
    result: { proposal_markdown: `Generated prose for ${documentId}.` },
  });
}

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

export function renderLoopHook(
  initialProject: Project,
  onCapture: (documentId: string) => void = () => undefined,
): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (project: Project) => void;
  readonly unmount: () => void;
} {
  let activeProject = initialProject;
  let current: HarnessSnapshot | undefined;
  let replaceProject: ((project: Project) => void) | undefined;

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(initialProject);
    replaceProject = setProject;
    // Accepted documents are recorded in a ref: tests only observe them
    // through snapshots, so the extra re-render would be pure overhead.
    const accepted = useRef<StudioDocument[]>([]);
    const hook = useWholeBookLoop({
      projectId: activeProject.id,
      provider: "mock",
      setProject,
      loadJobs: vi.fn(),
      captureAcceptedDocument: (documentId) => {
        onCapture(documentId);
        return (document) => {
          accepted.current = [...accepted.current, document];
        };
      },
    });
    current = { hook, project, accepted: accepted.current };
    return null;
  }

  const { container, root } = harness.mount(<Wrapper />);

  return {
    result: () => {
      if (current === undefined) throw new Error("Expected hook result after render.");
      return current;
    },
    rerender: (nextProject) => {
      activeProject = nextProject;
      act(() => {
        replaceProject?.(nextProject);
        root.render(<Wrapper />);
      });
    },
    // Unmount now and keep afterEach from unmounting the same root twice.
    unmount: () => {
      harness.unmount(container);
    },
  };
}

/** Release every step immediately while recording the exact call sequence. */
export function traceApiCalls(events: string[], refreshedProject: Project = baseProject): void {
  vi.mocked(streamProposal).mockImplementation(async ({ documentId }) => {
    events.push(`proposal:${documentId}`);
    return proposalJobFor(documentId);
  });
  vi.mocked(api.acceptProposal).mockImplementation(async (_projectId, jobId) => {
    events.push(`accept:${jobId}`);
    return proposalJobFor(jobId.replace("job-", ""));
  });
  vi.mocked(api.project).mockImplementation(async () => {
    events.push("refresh");
    return refreshedProject;
  });
  vi.mocked(api.document).mockImplementation(async (_projectId, documentId) => {
    const document = refreshedProject.documents.find((candidate) => candidate.id === documentId);
    if (!document || !("content_markdown" in document)) {
      throw new Error("Expected a complete current-Document fixture.");
    }
    return document as StudioDocument;
  });
}
