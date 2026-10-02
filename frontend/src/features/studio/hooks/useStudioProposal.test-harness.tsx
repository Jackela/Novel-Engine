import { act, useRef, useState } from "react";
import { afterEach, vi } from "vitest";

import type { ProposalStreamRequest } from "@/app/proposalStream";
import { streamProposal } from "@/app/proposalStream";
import type { Project, StudioDocument, StudioJob } from "@/app/types/studio";
import type { InspectorTab } from "@/features/studio/studioConstants";
import { chapter, job, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useStudioProposal } from "./useStudioProposal";

export type HookResult = ReturnType<typeof useStudioProposal>;

export interface HarnessSnapshot {
  readonly hook: HookResult;
  readonly project: Project | null;
  readonly inspector: InspectorTab;
  readonly error: string | null;
  readonly accepted: StudioDocument | null;
}

const harness = createMountHarness();

export const firstDocument = chapter("document-1", {
  title: "Chapter One",
  current_revision_id: "revision-1",
  content_markdown: "Original scene",
  revision_source: "author",
  word_count: 2,
});

export const secondDocument = {
  ...firstDocument,
  id: "document-2",
  title: "Chapter Two",
  current_revision_id: "revision-2",
};

export const baseProject = projectWith([firstDocument, secondDocument], {
  description: "A harbor of brass clocks.",
});

export const proposalJob = job({
  project_id: baseProject.id,
  document_id: firstDocument.id,
  result: { proposal_markdown: "A generated continuation." },
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

export function renderProposalHook(): {
  readonly result: () => HarnessSnapshot;
  readonly rerender: (document: StudioDocument) => void;
  readonly loadJobs: ReturnType<typeof vi.fn<() => void>>;
} {
  let activeDocument = firstDocument;
  let current: HarnessSnapshot | undefined;
  const loadJobs = vi.fn<() => void>();

  function Wrapper(): null {
    const [project, setProject] = useState<Project | null>(baseProject);
    const [inspector] = useState<InspectorTab>("history");
    const [error, setError] = useState<string | null>("previous error");
    // Captured through a ref: the accepted document is an observation for the
    // assertions, not rendered output, so it must not mint a state update.
    const acceptedRef = useRef<StudioDocument | null>(null);
    const hook = useStudioProposal(
      baseProject.id,
      activeDocument,
      project,
      setProject,
      setError,
      loadJobs,
      (documentId) =>
        documentId === activeDocument.id
          ? (document) => {
              acceptedRef.current = document;
            }
          : undefined,
    );
    current = { hook, project, inspector, error, accepted: acceptedRef.current };
    return null;
  }

  const { root } = harness.mount(<Wrapper />);

  const render = () => root.render(<Wrapper />);

  return {
    result: () => {
      if (current === undefined) {
        throw new Error("Expected hook result after render.");
      }
      return current;
    },
    rerender: (document) => {
      activeDocument = document;
      act(render);
    },
    loadJobs,
  };
}

export function deferredStream(): {
  requests: ProposalStreamRequest[];
  settle: (job: StudioJob | Promise<StudioJob>, failure?: unknown) => Promise<void>;
} {
  const requests: ProposalStreamRequest[] = [];
  const pending: Array<{
    resolve: (job: StudioJob) => void;
    reject: (reason: unknown) => void;
  }> = [];
  vi.mocked(streamProposal).mockImplementation(async (request) => {
    requests.push(request);
    return new Promise<StudioJob>((resolve, reject) => {
      pending.push({ resolve, reject });
    });
  });
  return {
    requests,
    settle: async (job, failure) => {
      const entry = pending.shift();
      if (entry === undefined) throw new Error("Expected a pending stream.");
      await act(async () => {
        if (failure !== undefined) {
          entry.reject(failure);
        } else {
          entry.resolve(await job);
        }
        await Promise.resolve();
      });
    },
  };
}
