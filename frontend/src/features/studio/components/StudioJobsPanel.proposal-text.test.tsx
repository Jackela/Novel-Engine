import { getByRole } from "@testing-library/dom";
import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/app/api";
import { job, jobSummary } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

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
});
