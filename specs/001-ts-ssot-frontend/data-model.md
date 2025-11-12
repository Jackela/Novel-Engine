# Data Model: Frontend Type Safety and Styling SSOT

## Entities

- DesignTokens
  - Fields: colors, typography, spacing, elevation, motion
  - Color: primary, secondary, background.{default,paper,tertiary}, border.{primary,secondary,focus}, text.{primary,secondary,tertiary,disabled}
  - Typography: families, sizes (display/heading/body/mono), weights, line-heights
  - Spacing: scale based on 4px/8px units
  - Elevation: shadow presets
  - Motion: durations, easings

- Theme
  - Derived from DesignTokens
  - Surfaces: palette (primary/secondary/background/text/divider), shape, shadows, components overrides

- QueryKeys
  - Stable identifiers for server-state caching/invalidation
  - Examples: ['characters','list'], ['characters','detail',name], ['stories','generation',id]

- DTOs (client-side)
  - Character: id, name, faction, role, description, stats, equipment[], relationships[], createdAt(ISO), updatedAt(ISO)
  - StoryProject: id, title, description, characters[], settings, status, createdAt(ISO), updatedAt(ISO), storyContent, metadata
  - GenerationStatus: generation_id, status, progress, stage, estimated_time_remaining

## Validation Rules

- Dates normalized from ISO strings at boundaries; internal components may use Date objects but serialization remains ISO.
- Tokens must satisfy WCAG 2.1 AA contrast for text on primary surfaces.
- Query keys must be pure and serializable.

## State Transitions (informal)

- Tokens change → triggers rebuild of generated CSS; no runtime mutation required.
- Read endpoint invalidation → cache invalidated → next read re-fetches and updates consumers.

