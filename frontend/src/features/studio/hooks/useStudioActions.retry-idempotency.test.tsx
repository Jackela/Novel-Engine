import { act, useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api, HttpError } from "@/app/api";
import { recordRetryAttemptSession } from "@/app/retryAttemptRegistry";
import type { Project } from "@/app/types/studio";
import { job, project } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { useStudioActions } from "./useStudioActions";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, retryJob: vi.fn<typeof actual.api.retryJob>() } };
});

const harness = createMountHarness();
const projectA = project({ id: "project-a" });

function rejectableDeferred<T>() {
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((_resolve, rejectValue) => {
    reject = rejectValue;
  });
  return { promise, reject };
}

beforeEach(() => {
  recordRetryAttemptSession({
    session_id: "session-a",
    kind: "owner",
    owner_id: "owner-a",
    expires_at: null,
  });
  vi.spyOn(crypto, "randomUUID")
    .mockReturnValueOnce("00000000-0000-4000-8000-000000000001")
    .mockReturnValueOnce("00000000-0000-4000-8000-000000000002")
    .mockReturnValueOnce("00000000-0000-4000-8000-000000000003");
});

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

function renderActions(target: Project = projectA) {
  let actions: ReturnType<typeof useStudioActions> | undefined;
  let error: string | null = null;
  const loadJobs = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);

  function Wrapper() {
    const [, setProject] = useState<Project | null>(target);
    const [visibleError, setError] = useState<string | null>(null);
    error = visibleError;
    actions = useStudioActions({
      project: target,
      projectId: target.id,
      setProject,
      setReviews: vi.fn(),
      setError,
      setActiveId: vi.fn(),
      settingsForm: { title: target.title, description: target.description, provider: "mock" },
      loadJobs,
    });
    return null;
  }

  const mounted = harness.mount(<Wrapper />);
  return {
    actions: () => {
      if (actions === undefined) throw new Error("Expected Studio actions.");
      return actions;
    },
    error: () => error,
    loadJobs,
    mounted,
  };
}

describe("useStudioActions retry attempt identity", () => {
  it("keeps retry pending through the terminal jobs refresh", async () => {
    const retryResponse = deferred<ReturnType<typeof job>>();
    const jobsResponse = deferred<void>();
    vi.mocked(api.retryJob).mockReturnValue(retryResponse.promise);
    const mounted = renderActions();
    mounted.loadJobs.mockReturnValue(jobsResponse.promise);

    let retry = Promise.resolve();
    act(() => {
      retry = mounted.actions().retryJob("source-job");
    });
    await vi.waitFor(() => expect(api.retryJob).toHaveBeenCalledTimes(1));
    expect(mounted.actions().retryingJobId).toBe("source-job");

    await act(async () => {
      retryResponse.resolve(job({ id: "retry-terminal" }));
      await Promise.resolve();
    });
    expect(mounted.loadJobs).toHaveBeenCalledWith("retry");
    expect(mounted.actions().retryingJobId).toBe("source-job");

    await act(async () => {
      jobsResponse.resolve(undefined);
      await retry;
    });
    expect(mounted.actions().retryingJobId).toBeNull();
  });

  it("retains an ambiguous key, then clears it only after a terminal response", async () => {
    vi.mocked(api.retryJob)
      .mockRejectedValueOnce(new HttpError("At capacity.", 503))
      .mockResolvedValue(job({ id: "retry-terminal", status: "failed" }));
    const mounted = renderActions();

    await act(async () => mounted.actions().retryJob("source-job"));
    await act(async () => mounted.actions().retryJob("source-job"));

    expect(api.retryJob).toHaveBeenNthCalledWith(
      1,
      "project-a",
      "source-job",
      "00000000-0000-4000-8000-000000000001",
    );
    expect(api.retryJob).toHaveBeenNthCalledWith(
      2,
      "project-a",
      "source-job",
      "00000000-0000-4000-8000-000000000001",
    );
    expect(mounted.loadJobs).toHaveBeenCalledWith("retry");

    await act(async () => mounted.actions().retryJob("source-job"));
    expect(api.retryJob).toHaveBeenLastCalledWith(
      "project-a",
      "source-job",
      "00000000-0000-4000-8000-000000000002",
    );
  });

  it.each([401, 403, 404, 422])("clears a definitively rejected %i attempt", async (status) => {
    vi.mocked(api.retryJob)
      .mockRejectedValueOnce(new HttpError("Rejected.", status))
      .mockResolvedValue(job({ id: "retry-terminal" }));
    const mounted = renderActions();

    await act(async () => mounted.actions().retryJob("source-job"));
    await act(async () => mounted.actions().retryJob("source-job"));

    expect(api.retryJob).toHaveBeenNthCalledWith(
      2,
      "project-a",
      "source-job",
      "00000000-0000-4000-8000-000000000002",
    );
  });

  it.each([
    ["409", new HttpError("Running.", 409)],
    ["500", new HttpError("Unknown.", 500)],
    ["transport", new Error("Connection closed.")],
    ["abort", new DOMException("Aborted", "AbortError")],
  ])("retains the key after %s unknown outcome", async (_label, failure) => {
    vi.mocked(api.retryJob)
      .mockRejectedValueOnce(failure)
      .mockResolvedValue(job({ id: "retry-terminal" }));
    const mounted = renderActions();

    await act(async () => mounted.actions().retryJob("source-job"));
    await act(async () => mounted.actions().retryJob("source-job"));

    expect(api.retryJob).toHaveBeenNthCalledWith(
      2,
      "project-a",
      "source-job",
      "00000000-0000-4000-8000-000000000001",
    );
  });

  it("retains an unknown A attempt across A-B-A without late error publication", async () => {
    const response = rejectableDeferred<never>();
    vi.mocked(api.retryJob).mockReturnValue(response.promise);
    const firstA = renderActions(projectA);
    let pending = Promise.resolve();
    act(() => {
      pending = firstA.actions().retryJob("source-job");
    });
    await vi.waitFor(() => expect(api.retryJob).toHaveBeenCalledTimes(1));
    harness.unmount(firstA.mounted.container);
    renderActions(project({ id: "project-b" }));

    await act(async () => {
      // A transport rejection settles after its workbench no longer owns UI.
      response.reject(new Error("lost"));
      await pending.catch(() => undefined);
    });

    expect(firstA.error()).toBeNull();
    harness.cleanup();
    vi.mocked(api.retryJob).mockResolvedValue(job({ id: "retry-terminal" }));
    const secondA = renderActions(projectA);
    await act(async () => secondA.actions().retryJob("source-job"));
    expect(api.retryJob).toHaveBeenLastCalledWith(
      "project-a",
      "source-job",
      "00000000-0000-4000-8000-000000000001",
    );
  });
});
