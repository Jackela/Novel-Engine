# Faction Intel Panel

## Overview

React component for displaying faction AI decision-making process and intent history.

## Requirements

### REQ-UI-001: Component Structure
The component SHALL display:
- Faction selector dropdown
- "Generate Intents" action button
- Current intents as cards with: action type, target, rationale, priority
- Intent history in collapsible accordion
- Loading state during generation

### REQ-UI-002: Intent Card Display
Each intent card SHALL show:
- Action type icon (color-coded: EXPAND=green, ATTACK=red, TRADE=blue, SABOTAGE=purple, STABILIZE=gray)
- Target name (if applicable)
- Rationale text
- Priority badge (1, 2, or 3)
- Select button (for PROPOSED intents)
- Status indicator

### REQ-UI-003: Loading State
During intent generation, the component SHALL display:
- Spinner or skeleton loader
- "Analyzing faction situation..." message
- Disabled "Generate Intents" button

### REQ-UI-004: Error Handling
On API error, the component SHALL display:
- Error message from API
- Retry button
- Option to view cached intents

### REQ-UI-005: Accessibility
The component SHALL meet WCAG 2.1 AA:
- Keyboard navigation for all interactions
- ARIA labels for icons and buttons
- Focus management on state changes
- Screen reader announcements for new intents

### REQ-UI-006: TanStack Query Integration
The component SHALL use TanStack Query:
- useMutation for generation requests
- useQuery for fetching intent history
- Automatic cache invalidation on generation

## Scenarios

### Scenario: Display Generated Intents
Given user is viewing faction "north-kingdom"
When "Generate Intents" is clicked
Then loading state SHALL be shown
And 3 intent cards SHALL appear when complete
And each card SHALL show action type with icon

### Scenario: Select an Intent
Given 3 PROPOSED intents are displayed
When user clicks "Select" on intent 2
Then intent 2 status SHALL change to SELECTED
And other intents SHALL remain PROPOSED
And success toast SHALL be shown

### Scenario: View History
Given faction has 10 historical intents
When user expands "History" accordion
Then all historical intents SHALL be displayed
And intents SHALL be sorted by creation date (newest first)
