# DashScope 20-Chapter Live Evidence

## Refresh Required

The previous checked-in evidence was captured against the removed story
workflow. It has been cleared from the active UAT baseline so it cannot be
mistaken for proof of the current local workspace path.

Refresh this file with a live DashScope run when a human-reviewed baseline is
needed:

```bash
uv run python scripts/uat/run_dashscope_longform_uat.py --target-chapters 20 --write-canonical-reports
```

The refreshed report must show:

- `POST /api/workspaces`
- `POST /api/workspaces/{workspace_id}/jobs` with `operation=run`
- `GET /api/workspaces/{workspace_id}`
- `POST /api/workspaces/{workspace_id}/jobs` with `operation=export`
- drafted chapters `>= 20`
- export outcome `exported`
- blocker count `0`

Warnings are expected to remain visible as editorial advice and do not block
export.
