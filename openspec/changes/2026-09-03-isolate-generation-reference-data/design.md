# Design: collision-free generation data boundaries

## Authority model

The system prompt is the sole system-instruction authority. The dedicated
author-instruction block may guide story behavior only when consistent with
system policy. Every value loaded from project documents or revisions is
reference data, regardless of whether its revision source is `author`,
`ai-accepted`, or `restore`, and regardless of Lore lifecycle status. `stable`
means eligible canon, not executable instruction.

The system prompt names the project outline and linked beat, prior-story
summary, recent chapter tail, Lorebook, and target manuscript as reference-only
blocks. Only delimiters emitted by the assembler structure the user message;
escaped bracket sequences inside a block are literal source text.

## Collision-free codec

One pure formatter owns dynamic prompt text. It first escapes the codec escape
character and then encodes `[` and `]` as visible Unicode escape sequences.
That ordering distinguishes a stored literal such as `\u005B` from a stored
`[` and permits a test reference decoder to recover the exact original string.
The production prompt path does not need or expose a decoder.

Encoding happens only at final rendering. Lore key matching and resident match
corpora continue to use raw values. The outline, beat title/content, prior
title/digest, recent text, Lore title and selected full/summary body all cross
the codec before interpolation. Lore budgeting measures the final encoded
section, preserving the existing definition that the budget applies to what is
actually rendered.

Author instructions use the same structural encoding before the existing
injection-phrase redaction. The redaction placeholder is server-generated and
remains readable. The manuscript keeps its existing JSON representation and
JSON-aware bracket escaping, which already distinguishes literal backslash
escapes through `JSON.stringify`.

For benign project content containing no square bracket or backslash, section
labels, order, headings, and prose bytes remain unchanged. The linked-beat
fixed explanation moves inside the outline delimiter so no dynamic beat value
is interpolated outside a reference block.

## Shared assembly

`buildProposalUserPrompt` remains the single interface. Synchronous generation,
SSE streaming, and keyed retry all call `buildProposalTask`; whole-book
generation uses the same streaming endpoint. No caller gets a parallel prompt
formatter or a raw-string bypass.

## Failure behavior

The codec is total for JavaScript strings and does not reject author content or
add a business error. Unexpected database, provider, or programming failures
remain visible. There is no raw-text fallback. Tests own a reference decoder
and assert `decode(encode(value)) === value` for Unicode, newlines, slashes,
reserved markers, and unpaired surrogates.

## Options rejected

- A prompt-injection phrase blacklist is incomplete, changes prose, and cannot
  prevent delimiter forgery.
- Escaping square brackets without escaping the escape character is ambiguous:
  a literal stored escape can collide with an encoded bracket.
- Canonical JSON per section gives strong parsing but changes every prompt,
  adds field-name/token overhead, and changes Lore budget promotion for benign
  content. It is unnecessary when the section contract and codec already make
  delimiter ownership testable.
- Base64 hides useful prose from the model and requires a decoding instruction.
- Treating `stable` Lore or an author outline as trusted instruction confuses
  provenance/content approval with provider authority.
