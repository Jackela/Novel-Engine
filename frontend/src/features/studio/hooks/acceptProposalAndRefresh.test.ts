import type { SetStateAction } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, HttpError } from "@/app/api";
import { ApiContractError } from "@/app/apiContract";
import type { Project, StudioDocument } from "@/app/types/studio";
import { chapter, job, projectWith } from "@/test/factories";
import { deferred } from "@/test/harness";
import { AcceptedProposalRefreshError, acceptProposalAndRefresh } from "./acceptProposalAndRefresh";
import * as diagnostics from "./reportUnexpectedError";

vi.mock("@/app/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/app/api")>();
  return {
    ...actual,
    api: { ...actual.api, acceptProposal: vi.fn(), document: vi.fn(), project: vi.fn() },
  };
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.resetAllMocks();
});

const before = chapter("one", { current_revision_id: "base" });
const accepted = { ...before, current_revision_id: "accepted", content_markdown: "Accepted prose" };
const restored = { ...before, current_revision_id: "restored", content_markdown: "Restored prose" };
const proposal = job({ result: { base_revision_id: "base", accepted_revision_id: "accepted" } });

function setup() {
  let project: Project | null = projectWith([before]);
  vi.mocked(api.acceptProposal).mockResolvedValue(proposal);
  vi.mocked(api.project).mockResolvedValue(projectWith([accepted]));
  vi.mocked(api.document).mockResolvedValue(accepted);
  const options = {
    projectId: before.project_id,
    proposalId: proposal.id,
    documentId: before.id,
    setProject: (action: SetStateAction<Project | null>) => {
      project = typeof action === "function" ? action(project) : action;
    },
    loadJobs: vi.fn(),
    onAcceptanceCommitted: vi.fn(),
  };
  return { options, project: () => project };
}

describe("accepted Proposal refresh boundaries", () => {
  it("retains a newer inactive-document shell when no active Draft was captured", async () => {
    const view = setup();
    const body = deferred<StudioDocument>();
    vi.mocked(api.document).mockReturnValueOnce(body.promise);
    const pending = acceptProposalAndRefresh(view.options);
    await vi.waitFor(() => expect(api.document).toHaveBeenCalled());
    view.options.setProject(projectWith([restored]));
    body.resolve(accepted);
    await pending;
    expect(view.project()?.documents[0]?.current_revision_id).toBe("restored");
    expect(view.options.onAcceptanceCommitted).toHaveBeenCalledOnce();
    expect(view.options.loadJobs).toHaveBeenCalledOnce();
  });

  it.each(["project", "document"] as const)(
    "preserves committed status and diagnostics when a current %s refresh fails",
    async (stage) => {
      const view = setup();
      const failure = new ApiContractError("accepted document");
      const diagnostic = vi
        .spyOn(diagnostics, "reportUnexpectedError")
        .mockImplementation(() => {});
      vi.mocked(api[stage]).mockRejectedValueOnce(failure);
      await expect(acceptProposalAndRefresh(view.options)).rejects.toMatchObject({
        name: AcceptedProposalRefreshError.name,
        cause: failure,
      });
      expect(diagnostic).toHaveBeenCalledWith("Proposal acceptance refresh failed.", failure);
      expect(view.options.onAcceptanceCommitted).toHaveBeenCalledOnce();
      expect(view.options.loadJobs).not.toHaveBeenCalled();
    },
  );

  it.each([
    new HttpError("Stale refresh", 503),
    new Error("Unexpected refresh"),
    new ApiContractError("project"),
  ])("does not publish a superseded shell failure (%s)", async (failure) => {
    const view = setup();
    let rejectShell!: (reason: unknown) => void;
    const shell = new Promise<Project>((_resolve, reject) => {
      rejectShell = reject;
    });
    vi.mocked(api.project).mockReturnValueOnce(shell);
    const diagnostic = vi.spyOn(diagnostics, "reportUnexpectedError").mockImplementation(() => {});
    let current = true;
    const reconcile = vi.fn();
    const pending = acceptProposalAndRefresh({
      ...view.options,
      acceptance: { isCurrent: () => current, reconcile },
    });
    await vi.waitFor(() => expect(api.project).toHaveBeenCalled());
    current = false;
    rejectShell(failure);
    await expect(pending).resolves.toBeNull();
    expect(reconcile).not.toHaveBeenCalled();
    expect(view.options.loadJobs).toHaveBeenCalledOnce();
    if (!(failure instanceof HttpError))
      expect(diagnostic).toHaveBeenCalledWith(
        "Superseded proposal acceptance refresh failed.",
        failure,
      );
    else expect(diagnostic).not.toHaveBeenCalled();
  });
});
