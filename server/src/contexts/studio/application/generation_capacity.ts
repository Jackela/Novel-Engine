import { GenerationCapacityExceededError } from "../domain/exceptions.js";
import { GENERATION_PROMPT_BYTE_LIMIT } from "../domain/generation_capacity_policy.js";

export { GENERATION_PROMPT_BYTE_LIMIT } from "../domain/generation_capacity_policy.js";

/**
 * Incremental prompt materializer. Reserved text is counted but not included
 * in the returned user prompt, allowing the system prompt to share one budget.
 */
export class BoundedPromptWriter {
  private readonly parts: string[] = [];
  private usedBytes: number;

  constructor(reservedText = "") {
    this.usedBytes = Buffer.byteLength(reservedText);
    if (this.usedBytes > GENERATION_PROMPT_BYTE_LIMIT) this.refuse();
  }

  /** Append one join-line, including its preceding newline after the first. */
  writeLine(fragment: string): void {
    const separatorBytes = this.parts.length === 0 ? 0 : 1;
    const fragmentBytes = Buffer.byteLength(fragment);
    if (fragmentBytes > GENERATION_PROMPT_BYTE_LIMIT - this.usedBytes - separatorBytes) {
      this.refuse();
    }
    this.usedBytes += separatorBytes + fragmentBytes;
    this.parts.push(fragment);
  }

  /** Materialize only the already-admitted user-prompt fragments. */
  finish(): string {
    return this.parts.join("\n");
  }

  private refuse(): never {
    throw new GenerationCapacityExceededError(
      "prompt_bytes",
      GENERATION_PROMPT_BYTE_LIMIT,
      GENERATION_PROMPT_BYTE_LIMIT + 1,
    );
  }
}
