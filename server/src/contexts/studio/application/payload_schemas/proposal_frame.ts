import { type Static, Type } from "@fastify/type-provider-typebox";
import { jobPayloadSchema } from "./job.js";

/**
 * Proposal SSE frame SSOT (#440): the terminal frame vocabulary of a streamed
 * proposal (#308). Frames ride a hijacked `text/event-stream` reply written
 * with `JSON.stringify`, so they never pass through a route response schema —
 * these declarations are the wire contract the generator types its output
 * with and the drift guard pins. The `done` frame carries the same job
 * payload SSOT as the synchronous generation landing.
 */

export const proposalDeltaFrameSchema = Type.Object(
  {
    type: Type.Literal("delta"),
    text: Type.String(),
  },
  { additionalProperties: false },
);

export const proposalDoneFrameSchema = Type.Object(
  {
    type: Type.Literal("done"),
    job: jobPayloadSchema,
  },
  { additionalProperties: false },
);

export const proposalErrorFrameSchema = Type.Object(
  {
    type: Type.Literal("error"),
    error: Type.Object(
      {
        code: Type.Literal("PROVIDER_FAILED"),
        message: Type.String(),
      },
      { additionalProperties: false },
    ),
  },
  { additionalProperties: false },
);

/** In-stream failures carry the failed-job message; codes stay closed. */
export type ProposalStreamError = Static<typeof proposalErrorFrameSchema>["error"];

export const proposalStreamFrameSchema = Type.Union([
  proposalDeltaFrameSchema,
  proposalDoneFrameSchema,
  proposalErrorFrameSchema,
]);

export type ProposalStreamFramePayload = Static<typeof proposalStreamFrameSchema>;
