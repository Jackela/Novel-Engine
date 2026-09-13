# Align the Lore lifecycle and budget contract

## Why

The canonical product specification still requires every matching Lore entry
to inject its current Markdown. The accepted domain vocabulary, ADR-0006, and
the running product instead gate injection to `stable` entries and use
budgeted progressive disclosure. The specification can therefore validate
while contradicting the behavior authors actually receive.

## What Changes

- Make the Lore lifecycle closed set, defaults, and legacy migration behavior
  explicit in the product contract.
- Require only non-empty, matching `stable` entries to participate in prompts.
- Specify summary-first progressive disclosure, deterministic full-text
  promotion, and the shared configurable character budget.
- Require synchronous, streaming, retry, and whole-book generation to use the
  same Lore assembly.

## Impact

- Aligns the canonical specification and documentation with already accepted
  and implemented behavior; no database or HTTP shape changes.
- Adds cross-boundary tests for the budget default and frontend lifecycle
  closed set.
- Corrects the repository OpenSpec skill so future changes target the active
  `novel-engine` capability.
