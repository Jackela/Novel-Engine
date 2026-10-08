import { ApiContractError, objectValue } from "./apiContract";
import type { StudioJob } from "./types/studio";

export type ProposalStreamFrame =
  | { type: "started"; operation_id: string }
  | { type: "delta"; text: string }
  | { type: "done"; job: StudioJob }
  | { type: "error"; error: { code: string; message: string } };

/** Runtime-validates one frame against the closed server frame contract. */
export function parseProposalStreamFrame(data: string): ProposalStreamFrame {
  let value: unknown;
  try {
    value = JSON.parse(data);
  } catch {
    throw new ApiContractError(`proposal frame: not JSON (${data.slice(0, 64)})`);
  }
  const frame = objectValue(value, "proposal frame");
  const type = frame.type;
  if (type === "started") {
    if (typeof frame.operation_id !== "string")
      throw new ApiContractError("proposal frame: started.operation_id");
    return { type: "started", operation_id: frame.operation_id };
  }
  if (type === "delta") {
    if (typeof frame.text !== "string") throw new ApiContractError("proposal frame: delta.text");
    return { type: "delta", text: frame.text };
  }
  if (type === "done") {
    if (typeof frame.job !== "object" || frame.job === null || Array.isArray(frame.job)) {
      throw new ApiContractError("proposal frame: done.job");
    }
    return frame as unknown as ProposalStreamFrame;
  }
  if (type === "error") {
    const error = objectValue(frame.error, "proposal frame.error");
    if (typeof error.code !== "string") throw new ApiContractError("proposal frame: error.code");
    if (typeof error.message !== "string")
      throw new ApiContractError("proposal frame: error.message");
    return {
      type: "error",
      error: { code: error.code, message: error.message },
    };
  }
  throw new ApiContractError(`proposal frame: unknown type (${String(type)})`);
}
