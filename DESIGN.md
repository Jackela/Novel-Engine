# Novel Studio Design Notes

## Typography

- Product UI uses self-hosted IBM Plex Sans Variable through Fontsource.
- `system-ui` is the fallback for environments that cannot load the bundled
  font.
- The writing surface intentionally uses the existing `ui-serif` stack for
  long-form reading and editing. This contrast is part of the product's
  writing-studio identity.

## Visual language

- The interface uses a restrained, high-contrast neutral canvas with teal as
  the semantic accent for primary actions, selection, focus, and positive
  state.
- Shared CSS tokens live in `frontend/src/index.css`; components should reuse
  those tokens instead of introducing one-off colors.
- Dense panels and standard tabs are intentional: the UI serves an active
  writing workflow, so consistency and task visibility take priority over
  decorative surfaces.

## Interaction

- Interactive controls preserve visible focus, disabled, loading, error, and
  selected states.
- Motion is limited to state feedback and respects
  `prefers-reduced-motion: reduce`.
