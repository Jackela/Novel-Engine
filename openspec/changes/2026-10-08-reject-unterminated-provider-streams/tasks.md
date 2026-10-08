## 1. Provider completion

- [x] 1.1 Add regression coverage for EOF without completion, including empty and heartbeat-only streams.
- [x] 1.2 Require protocol completion in compatible, native, and Responses Provider streams.
- [x] 1.3 Verify accepted completion signals, trailing usage and in-band errors, and cancellation or first-failure precedence.

## 2. Proposal outcome

- [x] 2.1 Verify unterminated streams produce `PROVIDER_FAILED` without `done`, preserve failed Job partial evidence and zero-token `unreported` usage, and leave the Revision unchanged.
- [x] 2.2 Verify streams are not automatically retried after frames have escaped.

## 3. Validation

- [x] 3.1 Run strict OpenSpec validation and applicable server checks on the integrated candidate.
- [x] 3.2 Record the fixed comparison SHA, candidate evidence, skipped checks, and remaining acceptance gates.
