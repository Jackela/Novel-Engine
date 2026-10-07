import { getAllByRole, getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import type { StudioJob } from "@/app/types/studio";
import { job, jobSummary } from "@/test/factories";
import { createMountHarness, deferred } from "@/test/harness";

import { StudioJobsPanel } from "./StudioJobsPanel";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: {
      ...actual.api,
      job: vi.fn<typeof actual.api.job>(),
    },
  };
});

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});

describe("StudioJobsPanel proposal text (DR-010)", () => {
  it("keeps a dismissed proposal's recorded text readable and copyable from its job row", async () => {
    const writeText = vi.fn<(text: string) => Promise<void>>().mockResolvedValue(undefined);
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.mocked(api.job).mockResolvedValue(
      job({
        id: "job-discarded",
        kind: "proposal",
        operation: "continue",
        status: "completed",
        result: { proposal_markdown: "A discarded scene, still readable." },
      }),
    );
    const mounted = harness.mount(
      <StudioJobsPanel
        projectId="project-1"
        jobs={[jobSummary({ id: "job-discarded", kind: "proposal", status: "completed" })]}
        onLoadJobs={vi.fn()}
        onRetryJob={vi.fn()}
      />,
    );

    const view = getByRole(mounted.container, "button", { name: "View proposal text" });
    await act(async () => {
      view.click();
      await Promise.resolve();
    });

    expect(api.job).toHaveBeenCalledWith("project-1", "job-discarded", expect.anything());
    expect(mounted.container.textContent).toContain("A discarded scene, still readable.");

    const copy = getByRole(mounted.container, "button", { name: "Copy" });
    await act(async () => {
      copy.click();
      await Promise.resolve();
    });
    expect(writeText).toHaveBeenCalledWith("A discarded scene, still readable.");
  });

  it("keeps the latest clicked proposal when an earlier read lands last", async () => {
    const first = deferred<StudioJob>();
    const second = deferred<StudioJob>();
    vi.mocked(api.job).mockImplementation((_projectId, jobId) =>
      jobId === "job-a" ? first.promise : second.promise,
    );
    const mounted = harness.mount(
      <StudioJobsPanel
        projectId="project-1"
        jobs={[
          jobSummary({ id: "job-a", kind: "proposal", status: "completed" }),
          jobSummary({ id: "job-b", kind: "proposal", status: "completed" }),
        ]}
        onLoadJobs={vi.fn()}
        onRetryJob={vi.fn()}
      />,
    );
    const viewButtons = () =>
      getAllByRole(mounted.container, "button", { name: "View proposal text" });

    // The author clicks A's read, then B's before either body arrives.
    act(() => viewButtons()[0]?.click());
    act(() => viewButtons()[1]?.click());

    await act(async () => {
      second.resolve(job({ id: "job-b", result: { proposal_markdown: "Second proposal body." } }));
      await second.promise;
    });
    expect(mounted.container.textContent).toContain("Second proposal body.");

    await act(async () => {
      first.resolve(job({ id: "job-a", result: { proposal_markdown: "First proposal body." } }));
      await first.promise;
    });
    // The late first read never replaces the author's latest choice.
    expect(mounted.container.textContent).toContain("Second proposal body.");
    expect(mounted.container.textContent).not.toContain("First proposal body.");
  });
});
