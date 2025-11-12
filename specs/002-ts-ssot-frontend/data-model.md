# Data Model: Styling SSOT and UI States

## Entities

1) DesignToken
- Attributes: name (string), category (color|spacing|typography|radius|motion), value (string|number), description (string)
- Rules: Names are kebab-case; removal or rename requires validation and migration guidance.

2) Theme
- Attributes: palette (map), typography (map), spacing (scale), radii (scale), shadows (scale)
- Relationship: Derived from DesignToken set; read-only output for app consumption.

3) ComponentStyleState
- Attributes: componentName (string), states (normal|hover|active|disabled|focus), tokenRefs (list)
- Relationship: References DesignToken via tokenRefs; no literal values.

4) ServerResource
- Attributes: key (string), state (idle|loading|success|error), data (unknown), error (string|object), updatedAt (datetime)
- Rules: Uses standardized fetch/caching/error handling; consumers render consistent UI states.

## Invariants

- Theme and CSS variables must originate from the same DesignToken set.
- UI components reference tokens, not literal visual values.
- ServerResource presentation follows unified loading/error patterns across primary flows.

