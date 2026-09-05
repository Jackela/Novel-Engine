import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, Review } from "@/app/types/studio";
import { projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, retryJob: vi.fn<typeof actual.api.retryJob>() },
  };
});

const projectFixture = projectWith([]);
const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("useStudioActions proposal audit gate", () => {
  it("does not retry a job while the project has an unaudited proposal outcome", async () => {
    const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    let actions: ReturnType<typeof useStudioActions> | undefined;

    function Wrapper() {
      const [project, setProject] = useState<Project | null>(projectFixture);
      const [, setReviews] = useState<Review[]>([]);
      const [, setError] = useState<string | null>(null);
      const [, setActiveId] = useState<string | null>(null);
      actions = useStudioActions({
        project,
        projectId: projectFixture.id,
        setProject,
        setReviews,
        setError,
        setActiveId,
        settingsForm: { title: "Project", description: "", provider: "mock" },
        loadJobs,
        isProposalActionGated: () => true,
      });
      return null;
    }

    harness.mount(<Wrapper />);
    if (!actions) throw new Error("Expected actions hook result after render.");

    await act(async () => actions?.retryJob("job-1"));

    expect(api.retryJob).not.toHaveBeenCalled();
    expect(loadJobs).not.toHaveBeenCalled();
    expect(actions.retryingJobId).toBeNull();
  });
});
