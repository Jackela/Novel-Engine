import { fireEvent, screen } from "@testing-library/dom";
import { act } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "@/app/api";
import { job, jobSummary } from "@/test/factories";
import { createMountHarness } from "@/test/harness";
import { StudioAcpJobActions } from "./StudioAcpJobActions";

vi.mock("@/app/api", async (original) => {
  const actual = await original<typeof import("@/app/api")>();
  return { ...actual, api: { ...actual.api, job: vi.fn<typeof actual.api.job>() } };
});

it("cancels a retry confirmation and never runs the job when outcomes are unknown", async () => {
  const retry = vi.fn();
  vi.mocked(api.job).mockResolvedValue(
    job({
      provider: "acp",
      result: {
        agent_execution: { operation_id: "operation", outcome_unknown: true, external_effects: [] },
      },
    }),
  );
  harness.mount(
    <StudioAcpJobActions
      job={jobSummary({ provider: "acp", status: "interrupted" })}
      projectId="project"
      disabled={false}
      onRetry={retry}
    />,
  );
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry continue" })));
  expect(screen.getByRole("button", { name: "I checked the working folder; retry" })).toBeTruthy();
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Cancel" })));
  expect(retry).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", { name: "I checked the working folder; retry" })).toBeNull();
});
it("retries without a file warning only when durable evidence explicitly records no effects", async () => {
  const retry = vi.fn();
  vi.mocked(api.job).mockResolvedValue(
    job({
      provider: "acp",
      result: {
        agent_execution: {
          operation_id: "operation",
          outcome_unknown: false,
          external_effects: [],
        },
      },
    }),
  );
  harness.mount(
    <StudioAcpJobActions
      job={jobSummary({ provider: "acp", status: "failed" })}
      projectId="project"
      disabled={false}
      onRetry={retry}
    />,
  );
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry continue" })));
  expect(retry).toHaveBeenCalledTimes(1);
  expect(screen.getByText("No file changes were recorded.")).toBeTruthy();
});
it("shows a failed evidence read and refuses to retry without it", async () => {
  const retry = vi.fn();
  vi.mocked(api.job).mockRejectedValue(new Error("Evidence unavailable"));
  harness.mount(
    <StudioAcpJobActions
      job={jobSummary({ provider: "acp", status: "failed" })}
      projectId="project"
      disabled={false}
      onRetry={retry}
    />,
  );
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry continue" })));
  expect(screen.getByRole("alert").textContent).toContain("Evidence unavailable");
  expect(retry).not.toHaveBeenCalled();
});
const harness = createMountHarness();
afterEach(() => {
  harness.cleanup();
  vi.resetAllMocks();
});
it("requires a fresh explicit confirmation before retrying an ACP job that changed files", async () => {
  const retry = vi.fn();
  vi.mocked(api.job).mockResolvedValue(
    job({
      provider: "acp",
      status: "failed",
      result: {
        agent_execution: {
          operation_id: "operation",
          outcome_unknown: false,
          external_effects: [
            {
              type: "tool",
              tool_id: "write",
              title: "Write notes",
              kind: "edit",
              status: "completed",
              target: "notes.md",
            },
          ],
        },
      },
    }),
  );
  harness.mount(
    <StudioAcpJobActions
      job={jobSummary({ provider: "acp", status: "failed", operation: "rewrite" })}
      projectId="project"
      disabled={false}
      onRetry={retry}
    />,
  );
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Retry rewrite" })));
  expect(retry).not.toHaveBeenCalled();
  expect(screen.getByText("notes.md")).toBeTruthy();
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "I checked the working folder; retry" })),
  );
  expect(retry).toHaveBeenCalledTimes(1);
});
