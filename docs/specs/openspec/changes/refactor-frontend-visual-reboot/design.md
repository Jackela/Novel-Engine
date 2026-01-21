## Context
- The UI currently meets functionality requirements but lacks a distinct visual identity.
- Dashboard layout rules must remain compliant with existing specs.
- Guest-first entry and auth flows must remain intact.

## Goals / Non-Goals
- Goals: new visual identity, stronger hierarchy, more intentional motion, cohesive typography, and refined surfaces.
- Non-Goals: changing API behavior, removing existing dashboard zones, or altering guest/auth flows.

## Decisions
- Establish a two-font pairing with explicit CSS variables for headings/body.
- Use a non-flat background treatment (gradient + subtle pattern) across key pages.
- Apply purposeful motion (page-load reveal + staggered content) with respect for reduced-motion.

## Risks / Trade-offs
- Larger CSS changes may require retuning layout spacing to preserve dashboard spec constraints.
- New typography and motion could expose edge cases in tests and snapshots.

## Migration Plan
- Introduce new design tokens and base styles.
- Update page layouts and shared components to consume the new tokens.
- Verify guest, login, and dashboard flows remain functional.

## Open Questions
- Should the visual direction lean more “hardware minimalism” (aluminum + glass) or “editorial” (paper + ink)?
- Which pages are in scope beyond Landing, Login, and Dashboard?
