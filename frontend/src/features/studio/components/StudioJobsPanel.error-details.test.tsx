import { afterEach, describe, expect, it, vi } from "vitest";

import { jobSummary } from "@/test/factories";
import { createMountHarness } from "@/test/harness";

import { StudioJobsPanel } from "./StudioJobsPanel";

/**
 * DR-021: the provider's raw failure report is English and may quote HTTP
 * details; the panel's primary line must stay localized while the raw report
 * lives behind the collapsed technical-details disclosure.
 */

const harness = createMountHarness();

afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});

describe("StudioJobsPanel provider failure details", () => {
  it("hides the provider's raw English report behind a collapsed technical-details disclosure", () => {
    const raw =
      "DashScope generation failed for step 'chapter_revision': provider returned HTTP 401.";
    const mounted = harness.mount(
      <StudioJobsPanel
        projectId="project-1"
        jobs={[jobSummary({ id: "job-1", operation: "rewrite", status: "failed", error: raw })]}
        onLoadJobs={vi.fn()}
        onRetryJob={vi.fn()}
      />,
    );

    const details = mounted.container.querySelector<HTMLDetailsElement>(".job-error__details");
    if (details === null) throw new Error("Expected the technical-details disclosure.");
    expect(details.open).toBe(false);
    expect(details.querySelector("summary")?.textContent).toBe("Technical details");
    expect(details.textContent).toContain(raw);

    const primary = mounted.container.querySelector(".job-error__primary");
    expect(primary?.textContent).toBe("This job failed.");
    expect(primary?.textContent).not.toContain("provider returned HTTP");
  });
});
