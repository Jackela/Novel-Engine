import { TextGenerationProviderError } from "../../../contexts/ai/application/ports/text_generation.js";

/**
 * Code-point accounting for generated proposals, shared by every proposal
 * pipeline (synchronous draft, #308 streaming, retry). Contract: lengths are
 * counted as Unicode code points, including one count for each unpaired
 * surrogate — not as UTF-16 code units — so the proposal limit means the same
 * thing for a whole string and for a stream of deltas; stream deltas are
 * tallied incrementally, joining a surrogate pair split across deltas.
 */

export const MAX_PROPOSAL_CODE_POINTS = 1_000_000;
export const OVERSIZED_PROPOSAL =
  "Generated proposal content exceeds 1,000,000 Unicode code point limit.";

export function assertProposalCodePointLimit(codePoints: number): void {
  if (codePoints > MAX_PROPOSAL_CODE_POINTS) {
    throw new TextGenerationProviderError(OVERSIZED_PROPOSAL);
  }
}

/** Count Unicode code points, including one count for each unpaired surrogate. */
export function proposalCodePointCount(text: string): number {
  let codePoints = 0;
  for (const _codePoint of text) codePoints += 1;
  return codePoints;
}

export interface ProposalCodePointCounter {
  codePoints: number;
  trailingHighSurrogate: boolean;
}

export function createProposalCodePointCounter(): ProposalCodePointCounter {
  return { codePoints: 0, trailingHighSurrogate: false };
}

function isHighSurrogate(codeUnit: number): boolean {
  return codeUnit >= 0xd800 && codeUnit <= 0xdbff;
}

function isLowSurrogate(codeUnit: number): boolean {
  return codeUnit >= 0xdc00 && codeUnit <= 0xdfff;
}

/** Incrementally count one delta, joining a surrogate pair split across deltas. */
export function includeProposalDelta(counter: ProposalCodePointCounter, delta: string): void {
  let index = 0;
  if (counter.trailingHighSurrogate && delta.length > 0) {
    counter.trailingHighSurrogate = false;
    if (isLowSurrogate(delta.charCodeAt(0))) index = 1;
  }
  while (index < delta.length) {
    const codeUnit = delta.charCodeAt(index);
    counter.codePoints += 1;
    assertProposalCodePointLimit(counter.codePoints);
    if (isHighSurrogate(codeUnit)) {
      const nextIndex = index + 1;
      if (nextIndex < delta.length && isLowSurrogate(delta.charCodeAt(nextIndex))) {
        index += 2;
        counter.trailingHighSurrogate = false;
        continue;
      }
      counter.trailingHighSurrogate = nextIndex === delta.length;
    } else {
      counter.trailingHighSurrogate = false;
    }
    index += 1;
  }
}
