# Tasks

## 1. Boundary contract

- [ ] 1.1 Add red tests with hostile markers, literal codec escape sequences,
      and instruction-looking text in author instruction, outline, linked beat,
      prior chapter title/body, recent text, Lore title, summary/full body, and
      manuscript values.
- [ ] 1.2 Assert each active context section has exactly one assembler-owned
      opener/closer and the reference codec round-trips every original value.
- [ ] 1.3 Update the system-prompt contract so every project-derived context
      block is reference data without system, developer, or user authority.

## 2. Single serialization path

- [ ] 2.1 Add one collision-free prompt-data codec that escapes its own escape
      character before reserved brackets and has a test-only reference decoder.
- [ ] 2.2 Migrate outline, beat, prior-story, and recent-text rendering to
      that codec inside assembler-owned markers without changing selection,
      reading order, or benign prompt bytes.
- [ ] 2.3 Migrate Lore title/mode/body rendering to the same record contract
      without changing lifecycle, matching, summaries, budget, or promotion
      order.
- [ ] 2.4 Encode author-instruction markers before phrase redaction, retain the
      manuscript's JSON-aware boundary, and keep fixed control prose outside
      all dynamic data blocks.

## 3. Pipeline parity and evidence

- [ ] 3.1 Prove synchronous, SSE streaming, keyed retry, and whole-book
      generation all use the same system prompt and serialized context.
- [ ] 3.2 Run resident/Lore/sanitization/proposal regressions and server
      type-check, lint, architecture, size, full tests, and strict OpenSpec.
- [ ] 3.3 Record fixed-SHA evidence and every skipped external or human gate;
      keep the change active until required CI is green, then merge the
      requirement into the canonical specification and archive it.
