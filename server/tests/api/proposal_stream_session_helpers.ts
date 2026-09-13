import { EventEmitter } from "node:events";

import type {
  ProposalStreamFrame,
  ProposalStreamSession,
} from "../../src/contexts/studio/application/proposal_streaming.js";

export class BackpressureResponse extends EventEmitter {
  readonly chunks: string[] = [];
  destroyed = false;
  writableFinished = false;

  constructor(private readonly backpressureOn: (chunk: string) => boolean) {
    super();
  }

  writeHead(): this {
    return this;
  }

  write(chunk: string): boolean {
    this.chunks.push(chunk);
    return !this.backpressureOn(chunk);
  }

  end(): this {
    this.writableFinished = true;
    return this;
  }

  destroy(): this {
    this.destroyed = true;
    return this;
  }
}

export async function releaseProposalStreamSession(
  session: ProposalStreamSession | undefined,
): Promise<void> {
  if (session === undefined) return;
  try {
    await session.frames.return();
  } finally {
    session.releaseCapacity();
  }
}

export async function collectProposalStream(
  session: ProposalStreamSession,
): Promise<ProposalStreamFrame[]> {
  const frames: ProposalStreamFrame[] = [];
  try {
    for await (const frame of session.frames) frames.push(frame);
    return frames;
  } finally {
    await releaseProposalStreamSession(session);
  }
}
