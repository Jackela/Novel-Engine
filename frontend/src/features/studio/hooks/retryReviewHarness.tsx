import { act, useState } from "react";
import { vi } from "vitest";

import { recordRetryAttemptSession } from "@/app/retryAttemptRegistry";
import type { Project } from "@/app/types/studio";
import { createMountHarness } from "@/test/harness";
import { useReviewHistory } from "./useReviewHistory";
import { useStudioActions } from "./useStudioActions";

/** Combines the existing Review resource and command owners for retry lifecycle evidence. */
export function retryReviewHarness(initialProject: Project) {
  recordRetryAttemptSession({
    session_id: "review-retry-session",
    kind: "owner",
    owner_id: "owner-a",
    expires_at: null,
  });
  let active = true;
  let project = initialProject;
  let history!: ReturnType<typeof useReviewHistory>;
  let actions!: ReturnType<typeof useStudioActions>;
  const mounts = createMountHarness();
  const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
  const invalidateReview = vi.fn(() => history.invalidate());
  const recheckProject = vi.fn().mockResolvedValue(true);
  const onSessionLost = vi.fn();

  function Probe() {
    const [, setProject] = useState<Project | null>(project);
    const [, setError] = useState<string | null>(null);
    history = useReviewHistory({ active, projectId: project.id, recheckProject, onSessionLost });
    actions = useStudioActions({
      project,
      projectId: project.id,
      setProject,
      setError,
      setActiveId: vi.fn(),
      setReviewPage: history.setFirstPage,
      invalidateReview,
      settingsForm: { title: project.title, description: project.description, provider: "mock" },
      loadJobs,
    });
    return null;
  }
  const mounted = mounts.mount(<Probe />);
  return {
    history: () => history,
    actions: () => actions,
    loadJobs,
    invalidateReview,
    activate(next: boolean) {
      active = next;
      act(() => mounted.root.render(<Probe />));
    },
    switchProject(next: Project) {
      project = next;
      act(() => mounted.root.render(<Probe />));
    },
    cleanup: mounts.cleanup,
  };
}
