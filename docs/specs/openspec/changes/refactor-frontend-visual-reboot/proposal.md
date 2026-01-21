# Change: Refactor frontend visual reboot

## Why
The current UI is functional but visually generic. A bold, cohesive visual system will strengthen the product narrative, improve perceived quality, and align the experience with a premium, Jobs-level aesthetic.

## What Changes
- Redesign the visual system (typography, color, surfaces, motion) with explicit design tokens.
- Rebuild key pages (landing, login, dashboard) to match the new visual system while preserving existing flows and requirements.
- Refresh layout composition and component styling to increase clarity, hierarchy, and delight without breaking existing routes or data flows.

## Impact
- Affected specs: design-system, frontend-workspace-ui, frontend-auth
- Affected code: frontend/src/pages/LandingPage.tsx, frontend/src/pages/LoginPage.tsx, frontend/src/features/dashboard/Dashboard.tsx, frontend/src/styles/*, frontend/src/components/layout/*
