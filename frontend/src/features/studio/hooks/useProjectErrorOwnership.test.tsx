import { act, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { Project, Review } from "@/app/types/studio";
import { projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { useOwnerKeyedErrors } from "./useOwnerKeyedErrors";
import { useStudioActions } from "./useStudioActions";
import { useStudioJobs } from "./useStudioJobs";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      createReview: vi.fn<typeof actual.api.createReview>(),
      jobs: vi.fn<typeof actual.api.jobs>(),
    },
  };
});

const harness = createMountHarness();
const project = projectWith([]);
const projectErrorSources = [
  "jobs",
  "review",
  "settings",
  "retryJob",
  "createDocument",
  "moveDocument",
] as const;

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderProjectOperations() {
  let current:
    | {
        readonly actions: ReturnType<typeof useStudioActions>;
        readonly jobs: ReturnType<typeof useStudioJobs>;
        readonly error: string | null;
      }
    | undefined;

  function Wrapper(): null {
    const [visibleProject, setProject] = useState<Project | null>(project);
    const [, setReviews] = useState<Review[]>([]);
    const [, setActiveId] = useState<string | null>(null);
    const errors = useOwnerKeyedErrors(project.id, projectErrorSources);
    const jobs = useStudioJobs(project.id, errors.publishers.jobs);
    current = {
      jobs,
      actions: useStudioActions({
        project: visibleProject,
        projectId: project.id,
        setProject,
        setReviews,
        setError: errors.publishers.jobs,
        errorPublishers: errors.publishers,
        setActiveId,
        settingsForm: { title: project.title, description: "", provider: "mock" },
        loadJobs: jobs.loadJobs,
      }),
      error: errors.error,
    };
    return null;
  }

  harness.mount(<Wrapper />);
  return {
    result: () => {
      if (!current) throw new Error("Expected project operations after render.");
      return current;
    },
  };
}

describe("project operation error ownership", () => {
  it("does not let a jobs success clear a review failure", async () => {
    vi.mocked(api.createReview).mockRejectedValue(new Error("Review failed."));
    vi.mocked(api.jobs).mockResolvedValue({ jobs: [] });
    const view = renderProjectOperations();

    await act(async () => view.result().actions.runReview());
    expect(view.result().error).toBe("Review failed.");

    await act(async () => view.result().jobs.loadJobs("refresh"));
    expect(view.result().error).toBe("Review failed.");
  });
});
