import { expect, it } from "vitest";
import { job } from "@/test/factories";
import { parseJob } from "./apiWorkflowContract";
import { parseAgentExecution } from "./parseAgentExecution";
import { parseAiOperationEvent } from "./parseAiOperationEvent";

it("retains redacted durable file actions and unknown outcome on a failed Job", () => {
  const parsed = parseJob({
    ...job({ provider: "acp", status: "failed" }),
    result: {
      agent_execution: {
        operation_id: "operation",
        outcome_unknown: true,
        external_effects: [
          {
            tool_id: "write",
            title: "Write notes",
            kind: "edit",
            status: "completed",
            target: "notes.md",
            arguments: "private",
          },
        ],
      },
    },
  });
  expect(parsed.result.agent_execution).toEqual({
    operation_id: "operation",
    outcome_unknown: true,
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
  });
  expect(parseJob(job()).result.agent_execution).toBeUndefined();
});
it.each([
  { type: "ready" },
  { type: "tool", title: "Read", kind: "read", tool_id: "read", status: "pending", target: 1 },
  { type: "permission", permission_id: "p", tool: {}, options: [] },
  {
    type: "permission",
    permission_id: "p",
    tool: { title: "Write", kind: "edit" },
    options: [null],
  },
  { type: "completed", external_effects: "rollback" },
  { type: "error", external_effects: "unknown", message: 1 },
  { type: "thinking", text: "private" },
])("rejects malformed or private events at the public boundary", (value) => {
  expect(() => parseAiOperationEvent(value)).toThrow();
});
it("accepts explicit none and unknown terminal effects without inventing a rollback", () => {
  expect(parseAiOperationEvent({ type: "completed", external_effects: "none" })).toEqual({
    type: "completed",
    external_effects: "none",
  });
  expect(
    parseAiOperationEvent({
      type: "error",
      external_effects: "unknown",
      message: "Operation failed",
    }),
  ).toEqual({ type: "error", external_effects: "unknown", message: "Operation failed" });
  expect(() =>
    parseAgentExecution({
      operation_id: "operation",
      external_effects: [],
      outcome_unknown: "yes",
    }),
  ).toThrow();
});
