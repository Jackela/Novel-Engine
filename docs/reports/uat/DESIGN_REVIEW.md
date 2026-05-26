# Design Review

This review is intentionally strict. It focuses on end-user clarity and release risk, not implementation effort.

## Findings

### P2: Long-form truth is now gated through the workspace API, but still expensive

The long-form DashScope run now targets the workspace/job API instead of the removed synchronous story pipeline. That closes the biggest trust gap for the local-first engine. The residual weakness is cost and runtime: the live gate is still materially slower and more expensive than the deterministic suite.

### P2: Guided workspace is clearer, but run diagnostics are still dense

The story page now centers the local workspace, chapter list, job controls, review report, and export state. The remaining usability debt is density in the run journal and metadata panels. Power users benefit from it; first-time users still have to learn a lot once they expand beyond the guided path.

### P2: Session catalog architecture is correct, but still browser-profile scoped

The product no longer treats one opaque localStorage blob as authority. Session restore is validated against the server, guest/user contexts coexist, and story/run/view selection is stored per session. The remaining limitation is scope: one browser profile still owns one local catalog, so cross-device restore and richer account management remain future work.

### P2: Library ergonomics are functional, not yet power-user grade

Multi-manuscript switching, URL-addressed story selection, and session-aware restore are now in place. The library still lacks search, filters, grouping, and stronger recency/favorite affordances.

### P3: Long-run progress remains thin

The product exposes stage history, playback evidence, and gate outcomes, but long external-provider runs still surface progress mostly as stage transitions and busy state. For 20-chapter runs, richer queue/progress semantics would still help.

## What This Redesign Fixed

- removed the hidden coupling between create-form export state and current-workspace reruns
- made session identity and workspace scope visible in both the shell chrome and the workshop
- promoted manuscript switching, run provenance, and playback into explicit surfaces
- replaced blind localStorage session restore with a validated session catalog plus URL-addressed story/run/view restore
- aligned browser automation with actual user-facing controls instead of incidental layout
- hardened the long-form workflow against real DashScope payload variance and timeout behavior
- moved the primary author path to local workspaces, complete chapter Markdown, sidecar metadata, and resumable run journals
- changed review semantics so only blockers prevent export while warnings remain editorial advice
- removed the old story-specific automatic revision loop from the primary product path
- split PR evidence from canonical UAT evidence so required live gates do not rewrite tracked docs on every branch run

## Release Recommendation

The current design is acceptable for continued feature work and controlled external evaluation. It has a required real-provider workspace gate, blocker-only export semantics, validated session restore, and browser-proven workspace operation. It is not yet the final shape of a polished author product.

The next design iteration should focus on:

- stronger prose-level rewrite briefs around continuity drift
- more varied chapter openings, turns, and endings instead of deterministic smoke-test cadence
- progressive disclosure for first-time users
- richer long-run progress feedback
- stronger differentiation between mutable workspace state and historical playback evidence
