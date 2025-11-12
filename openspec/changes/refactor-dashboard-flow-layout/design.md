# Design: Flow-based Adaptive Dashboard Layout

## Goals
1. Reduce perceived crowding by collapsing the dashboard into a handful of semantic zones whose width/height responds to real content.
2. Enable AI-generated/dynamic feeds to grow without breaking layout by using flow layout + virtualization instead of fixed tile sizes.
3. Preserve responsive behavior (desktop/tablet/mobile) while adding semantic hooks for automation (e.g., `data-role="stream-feed"`).

## Architecture Overview
- Introduce a `DashboardZones` orchestrator that receives a declarative config:
  ```ts
  type ZoneConfig = {
    id: 'control' | 'stream' | 'signals' | 'pipeline';
    priority: number;           // drives column span on desktop
    minColumns: number;         // min number of auto-fit columns
    maxColumns?: number;        // optional cap
    breakpointBehavior: { desktop: 'flow' | 'stack'; tablet: 'stack'; mobile: 'tabs' | 'accordion' };
  }
  ```
- Desktop `BentoGrid` becomes a lightweight wrapper that sets `grid-template-columns: repeat(auto-fit, minmax(260px, 1fr))`, `grid-auto-flow: dense`, and larger `gap`. Each zone renders inside a `<section data-role="...">` with internal flexbox layout.
- Zones host composite panels:
  - **Control Cluster**: combines QuickActions + RunState summary. Buttons left, run state right; uses responsive flex.
  - **NarrativeActivityPanel**: tabs between Narrative timeline and Activity feed on narrow screens; on desktop shows two columns in same card.
  - **SystemSignalsPanel**: tabs between Performance metrics and Event Cascade; virtualization for long event list.
  - **PipelinePanel**: Turn pipeline steps with integrated run summary; extends full width on desktop, collapses to accordion on tablet, to tab on mobile.

## Components & Responsibilities
| Component | Changes |
| --- | --- |
| `Dashboard.tsx` | Replace direct tile grid with `DashboardZones`. Provide semantic configs, pass `data-role` markers, share run state props. |
| `QuickActions.tsx` | Add run summary section, expose `data-role="quick-actions"`, support flexible layout (buttons wrap). |
| `TurnPipelineStatus.tsx` | Expand to include Run State info (phase, completion). Provide internal scroll when steps exceed viewport. |
| `NarrativeTimeline.tsx` & `RealTimeActivity.tsx` | Compose via new `NarrativeActivityPanel.tsx` to coordinate tabs, virtualization, shared skeletons. |
| `PerformanceMetrics.tsx` & `EventCascadeFlow.tsx` | Compose via `SystemSignalsPanel.tsx`. |
| `MobileTabbedDashboard.tsx` | Accept the same zone config to ensure consistent ordering; reorder tabs (Overview, Streams, Metrics). |
| Styles | Add flow layout CSS (auto-fit grid, larger gaps, container queries). Remove legacy `.tile-large`/`.tile-medium` assumptions. |

## Data/Test Considerations
- Playwright: selectors move to zone-level IDs (e.g., `data-testid="zone-control"`). Quick action buttons keep existing IDs. Activity feed virtualization still needs deterministic sample data for tests.
- Vitest: add coverage for new panel components and ensure render logic respects priority weights.
- act workflows: unchanged but must rerun to confirm.

## Open Questions / Risks
1. **Virtualization strategy**: For now, implement simple height capping with scroll; true virtualization can be deferred if performance remains acceptable.
2. **Legacy CSS**: Removing `.tile-*` classes may affect other dashboards; audit `frontend/src/components` for reuse before deleting.
3. **Accessibility**: Need to ensure new tab/accordion patterns have proper aria roles.
