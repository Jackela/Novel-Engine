# Tasks

- [x] 1. Add failing unit tests proving both HTTP adapters and their streaming
      path never read or disclose a non-success response body.
- [x] 2. Add failing integration tests proving canary values never enter job
      errors, event details, JSON job responses, later job reads, or SSE
      frames.
- [x] 3. Narrow `httpStatusFailure` to trusted context plus numeric status;
      remove the credential-bearing diagnostic field and body redaction path.
- [x] 4. Preserve status-based retry behavior for 401, 429, and persistent 503
      failures while updating exact safe-message assertions.
- [x] 5. Run Provider tests, proposal API/SSE tests, server quality gates, full
      server tests, and strict OpenSpec validation; complete dual-axis review.
