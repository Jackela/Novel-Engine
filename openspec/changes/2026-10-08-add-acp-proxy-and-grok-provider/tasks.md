## 1. Proxy transport

- [x] 1.1 Add failing public-interface tests for authenticated WS to stdio relay.
- [x] 1.2 Implement independent launch, framing, limits, token handling and cleanup.
- [x] 1.3 Integrate serve/connect into the existing CLI and verify shim interoperability.

## 2. Provider and interaction

- [x] 2.1 Add ACP discovery/configuration and confirmed model resolution.
- [x] 2.2 Implement all four steps, incremental prose, schema checks and safe usage.
- [x] 2.3 Add scoped execution observation and one-time permission decisions.
- [x] 2.4 Verify cancellation, failures, no automatic prompt replay and tool effects.

## 3. Studio

- [x] 3.1 Add bilingual Provider guidance, tool progress and permission controls.
- [x] 3.2 Connect every AI operation, including Review/Lore, to interaction lifecycle.
- [x] 3.3 Verify early streaming status, navigation, keyboard and error recovery.

## 4. Review

- [x] 4.1 Reproduce missing source text and revision identity through the provider seam.
- [x] 4.2 Supply captured source under the shared budget and preserve snapshot binding.
- [x] 4.3 Verify unchanged trial rules, source races and over-budget refusal.

## 5. Acceptance and evidence

- [x] 5.1 Regenerate OpenAPI/types deliberately and validate all applicable gates.
- [ ] 5.2 Run real configured Grok and browser/isolated deployment scenarios.
  - Partial: real Grok, Chromium/Chrome and isolated Compose exercised; native Grok permission request did not occur, final cloud tasks timed out, Firefox/Safari and reader/human gates remain open. See the acceptance report and registry. No release acceptance implied.
- [x] 5.3 Record complete specification/historical matrices and reproduced findings.
- [x] 5.4 Report current-version, historical-remediation and release-readiness states.
- [x] 5.5 Leave human, candidate-CI and release stages explicitly unclosed where not run.
