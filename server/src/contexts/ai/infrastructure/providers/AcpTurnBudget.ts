import {
  TextGenerationCancelledError,
  TextGenerationProviderError,
} from "../../application/ports/text_generation.js";
/** Finite handshake, execution and overall budgets; permission waiting pauses execution only. */
export class AcpTurnBudget {
  readonly controller = new AbortController();
  readonly signal = this.controller.signal;
  failure: unknown = new TextGenerationCancelledError();
  private timer: ReturnType<typeof setTimeout>;
  private readonly overall: ReturnType<typeof setTimeout>;
  private deadline: number;
  private remaining: number;
  private paused = 0;
  private readonly abort: () => void;
  constructor(
    handshakeMs: number,
    overallMs: number,
    private readonly external?: AbortSignal,
  ) {
    this.remaining = handshakeMs;
    this.deadline = Date.now() + handshakeMs;
    this.timer = this.timeout(handshakeMs);
    this.overall = setTimeout(
      () => this.fail(new TextGenerationProviderError("ACP overall timeout.")),
      overallMs,
    );
    this.abort = () => this.fail(new TextGenerationCancelledError());
    external?.addEventListener("abort", this.abort, { once: true });
    if (external?.aborted) this.abort();
  }
  private timeout(ms: number): ReturnType<typeof setTimeout> {
    return setTimeout(
      () => this.fail(new TextGenerationProviderError("ACP execution or handshake timeout.")),
      ms,
    );
  }
  fail(error: unknown): void {
    if (!this.signal.aborted) {
      this.failure = error;
      this.controller.abort();
    }
  }
  startExecution(ms: number): void {
    clearTimeout(this.timer);
    this.remaining = ms;
    this.deadline = Date.now() + ms;
    this.timer = this.timeout(ms);
  }
  pause(): void {
    this.paused += 1;
    if (this.paused > 1) return;
    this.remaining = Math.max(1, this.deadline - Date.now());
    clearTimeout(this.timer);
  }
  resume(): void {
    this.paused = Math.max(0, this.paused - 1);
    if (this.paused > 0) return;
    if (!this.signal.aborted) {
      this.deadline = Date.now() + this.remaining;
      this.timer = this.timeout(this.remaining);
    }
  }
  async wait<T>(pending: Promise<T>): Promise<T> {
    if (this.signal.aborted) {
      void pending.catch(() => {});
      throw this.failure;
    }
    let interrupt = (): void => {};
    const failed = new Promise<never>((_resolve, reject) => {
      interrupt = () => reject(this.failure);
      this.signal.addEventListener("abort", interrupt, { once: true });
    });
    try {
      return await Promise.race([pending, failed]);
    } finally {
      this.signal.removeEventListener("abort", interrupt);
    }
  }
  close(): void {
    clearTimeout(this.timer);
    clearTimeout(this.overall);
    this.external?.removeEventListener("abort", this.abort);
  }
}
