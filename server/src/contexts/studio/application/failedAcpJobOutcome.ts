import type { TextGenerationExecutionOptions } from "../../../contexts/ai/application/ports/text_generation.js";
import { failedJobOutcome } from "./failed_job_input.js";
import { dumpJson, safeLoadJson } from "./payloads.js";
/** Preserve prior result fields and safe ACP tool uncertainty on one failed retry transition. */
export function failedAcpJobOutcome(
  retry: { provider: string; resultJson: string },
  message: string,
  now: Date,
  execution?: TextGenerationExecutionOptions,
) {
  const failed = failedJobOutcome(message, now);
  return retry.provider === "acp" && execution?.agentExecution !== undefined
    ? {
        ...failed,
        resultJson: dumpJson({
          ...safeLoadJson(retry.resultJson),
          agent_execution: execution.agentExecution,
        }),
      }
    : failed;
}
