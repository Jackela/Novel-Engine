import { act, useLayoutEffect } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Project } from "@/app/types/studio";
import { chapter, projectWith } from "@/test/factories";
import { createMountHarness } from "@/test/harness";
import type { AcceptedDocumentCapture, CaptureAcceptedDocument } from "./useAcceptanceCapture";
import { useStudioGeneration } from "./useStudioGeneration";

const captures: Partial<Record<"proposal" | "wholeBook", CaptureAcceptedDocument>> = {};

vi.mock("./useStudioJobAudit", () => ({
  useStudioJobAudit: () => ({ loadJobs: () => undefined, proposalAudit: {} }),
}));
vi.mock("./useStudioProposal", () => ({
  useStudioProposal: (
    ...args: Parameters<typeof import("./useStudioProposal").useStudioProposal>
  ) => {
    captures.proposal = args[6];
    return {};
  },
}));
vi.mock("./useWholeBookLoop", () => ({
  useWholeBookLoop: (
    options: Parameters<typeof import("./useWholeBookLoop").useWholeBookLoop>[0],
  ) => {
    captures.wholeBook = options.captureAcceptedDocument;
    return {};
  },
}));

const harness = createMountHarness();
const target = chapter("target", { current_revision_id: "target-r1" });
const other = chapter("other", { current_revision_id: "other-r1" });
const original = projectWith([target, other]);
const ignore = () => undefined;

afterEach(() => {
  harness.cleanup();
  delete captures.proposal;
  delete captures.wholeBook;
});

/** Reads the existing async capture during commit, before any passive effects can publish. */
function observeCommitCurrency(surface: "proposal" | "wholeBook", nextProject: Project) {
  let acceptance: AcceptedDocumentCapture | undefined;
  const observations: boolean[] = [];
  function Probe({ project }: { project: Project }) {
    useStudioGeneration({
      projectId: project.id,
      activeDocument: other,
      project,
      setProject: ignore,
      setProposalError: ignore,
      setJobsError: ignore,
      captureAcceptance: ignore,
    });
    useLayoutEffect(() => {
      acceptance ??= captures[surface]?.(target.id);
      if (!acceptance) throw new Error("Expected generation's captured revision authority");
      observations.push(acceptance.isCurrent());
    });
    return null;
  }
  const { root } = harness.mount(<Probe project={original} />);
  act(() => root.render(<Probe project={nextProject} />));
  return observations;
}

describe.each(["proposal", "wholeBook"] as const)("%s committed revision authority", (surface) => {
  it("invalidates an old refresh as soon as a newer target revision commits", () => {
    const refreshed = projectWith([{ ...target, current_revision_id: "target-r2" }, other]);
    expect(observeCommitCurrency(surface, refreshed)).toEqual([true, false]);
  });

  it("retains a current refresh when the target revision is unchanged", () => {
    expect(observeCommitCurrency(surface, projectWith([target, other]))).toEqual([true, true]);
  });

  it("does not supersede the target refresh when only another document commits", () => {
    const changedOther = projectWith([target, { ...other, current_revision_id: "other-r2" }]);
    expect(observeCommitCurrency(surface, changedOther)).toEqual([true, true]);
  });
});
