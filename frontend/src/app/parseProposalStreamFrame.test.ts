import { expect, it } from "vitest";
import { ProposalStreamParser } from "./proposalStream";

it("accepts the explicit ACP started frame but still rejects unknown frames", () => {
  expect(
    new ProposalStreamParser().append('data: {"type":"started","operation_id":"operation"}\n\n'),
  ).toEqual([{ type: "started", operation_id: "operation" }]);
  expect(() =>
    new ProposalStreamParser().append('data: {"type":"thinking","text":"private"}\n\n'),
  ).toThrow("unknown type");
});
