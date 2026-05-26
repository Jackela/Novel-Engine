# UAT Reports

The canonical UAT package for the author shell lives in this folder. It is split into deterministic regression coverage, one long-form live evidence report, and a severity-ordered design review.

## Current Documents

- [VERIFICATION_MATRIX](./VERIFICATION_MATRIX.md) - flow-by-flow coverage map for API, browser, and manual live validation
- [LONGFORM_DASHSCOPE_LIVE_EVIDENCE](./LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md) - output location for the 20-chapter manual live gate
- [DESIGN_REVIEW](./DESIGN_REVIEW.md) - strict review of the current product design, remaining weaknesses, and release risks

## Manual Live Gate

Run the canonical live gate with:

```bash
python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20
```

This command starts a clean local backend, uses the real workspace API, drafts at least 20 chapter Markdown files with DashScope, reviews the local workspace, exports the manuscript, and writes:

- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.md`
- `docs/reports/uat/LONGFORM_DASHSCOPE_LIVE_EVIDENCE.json`

It fails on missing DashScope configuration, incomplete chapter delivery, missing review evidence, export blockers, or failed export outcome. Warnings are captured as editorial advice and do not fail the export gate.
