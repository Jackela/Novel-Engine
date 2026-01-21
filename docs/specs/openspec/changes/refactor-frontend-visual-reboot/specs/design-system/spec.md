## ADDED Requirements
### Requirement: Visual identity tokens are explicit and consistent
The UI MUST define and consume explicit CSS variables for typography, color, spacing, and elevation so the visual system is cohesive and reusable.

#### Scenario: Tokenized styling on core pages
- **WHEN** the Landing, Login, or Dashboard pages render
- **THEN** typography, color, and surface styles are driven by shared CSS variables rather than ad-hoc values.

### Requirement: Purposeful motion with reduced-motion support
The UI MUST provide a small set of intentional motion patterns (page-load reveal, staggered content) and respect `prefers-reduced-motion`.

#### Scenario: Reduced motion preference
- **GIVEN** the user prefers reduced motion
- **WHEN** the page loads
- **THEN** animations are disabled or simplified to non-motion alternatives.

### Requirement: Layered surfaces and non-flat backgrounds
The UI MUST use layered surfaces (cards/panels) and a non-flat background treatment to create depth without sacrificing readability.

#### Scenario: Surface hierarchy
- **WHEN** the dashboard renders
- **THEN** primary panels sit on elevated surfaces with clear separation from the background.
