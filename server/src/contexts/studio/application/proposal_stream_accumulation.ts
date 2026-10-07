import type {
  TextGenerationStreamOptions,
  TextGenerationStreamOutcome,
  TextGenerationTask,
} from "../../../contexts/ai/application/ports/text_generation.js";
import type { ProposalStreamFramePayload } from "./payload_schemas/proposal_frame.js";
import { createProposalCodePointCounter, includeProposalDelta } from "./proposal_landing.js";

/**
 * The streaming twin's delta loop: consumes the provider stream, counts code
 * points, accumulates the proposal markdown into the caller-owned sink, and
 * re-emits each delta as a `delta` frame. Returns the provider-reported
 * outcome once the stream completes; an abort and any provider failure
 * propagate to the caller's existing cancel/failure handling, and the sink
 * keeps the text read so far readable for a mid-stream failure landing
 * (#DR-006) — a completed stream drains it.
 */
export async function* accumulateStreamedDeltas(
  generate: (
    task: TextGenerationTask,
    options?: TextGenerationStreamOptions,
  ) => AsyncGenerator<string, void, void>,
  task: TextGenerationTask,
  signal: AbortSignal | undefined,
  // Caller-owned sink so a mid-stream failure can still read the text (#DR-006).
  accumulated: string[],
): AsyncGenerator<
  ProposalStreamFramePayload,
  { reported: TextGenerationStreamOutcome | undefined },
  void
> {
  const codePoints = createProposalCodePointCounter();
  let reported: TextGenerationStreamOutcome | undefined;
  for await (const delta of generate(task, {
    signal,
    onOutcome: (value) => {
      reported = value;
    },
  })) {
    includeProposalDelta(codePoints, delta);
    accumulated.push(delta);
    yield { type: "delta", text: delta };
  }
  return { reported };
}
