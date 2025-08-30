# Emergent Narrative Dashboard - UI Design Specification

## Document Overview

This specification defines the complete UI design for Novel Engine's Emergent Narrative Dashboard - a sophisticated real-time visualization interface for monitoring emergent storytelling across characters, world state, and narrative arcs using Bento Grid layout principles.

**Target Users**: Game Masters, Narrative Designers, System Administrators
**Primary Use Cases**: Real-time narrative monitoring, story analysis, performance tracking
**Technical Foundation**: React/TypeScript with CSS Grid, WebSocket integration

---

## 1. Layout Architecture

### 1.1 Grid System Foundation

The dashboard uses a **12-column CSS Grid system** with responsive breakpoints following Bento Grid principles:

```
Grid Configuration:
- Desktop (≥1440px): 12-column grid, 1200px max-width
- Tablet (768px - 1439px): 8-column grid, full-width
- Mobile (≤767px): Single column stack, full-width

Grid Gaps:
- Desktop: 24px horizontal, 20px vertical
- Tablet: 20px horizontal, 16px vertical  
- Mobile: 16px horizontal, 12px vertical
```

### 1.2 Primary Layout Structure

**Overall Dashboard Composition (Desktop - 12 columns):**

```
┌─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│     Header Navigation Bar (cols 1-12, height: 64px)                  │
├─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┤
│                                                                       │
│  A. World State Map        │  B. Real-time Activity    │ C. Perf     │
│     (cols 1-6)             │     (cols 7-10)          │    Metrics   │
│     Height: 320px          │     Height: 160px         │    (11-12)  │
│                            │                           │    160px    │
│                            ├───────────────────────────┼─────────────┤
│                            │  D. Turn Pipeline Status  │ E. Quick    │
│                            │     (cols 7-10)          │    Actions  │
│                            │     Height: 160px         │    (11-12)  │
│                            │                           │    160px    │
├────────────────────────────┼───────────────────────────┴─────────────┤
│  F. Character Networks     │  G. Event Cascade Flow                  │
│     (cols 1-6)             │     (cols 7-12)                        │
│     Height: 280px          │     Height: 280px                       │
├────────────────────────────┴─────────────────────────────────────────┤
│  H. Narrative Arc Timeline                                           │
│     (cols 1-12)                                                      │
│     Height: 200px                                                    │
├──────────────────────────────────────────────────────────────────────┤
│  I. Analytics Dashboard                                              │
│     (cols 1-12)                                                      │
│     Height: 240px (collapsible)                                     │
└──────────────────────────────────────────────────────────────────────┘
```

**Total Dashboard Height**: ~1484px (scrollable after viewport)

### 1.3 Responsive Behavior

**Tablet Layout (768px - 1439px, 8 columns):**
```
- World State Map: cols 1-5, height 300px
- Performance Metrics: cols 6-8, height 150px  
- Real-time Activity: cols 6-8, height 150px (stacked below Performance)
- Turn Pipeline: cols 1-8, height 140px
- Character Networks: cols 1-4, height 260px
- Event Cascade: cols 5-8, height 260px
- Narrative Timeline: cols 1-8, height 180px
- Analytics: cols 1-8, height 220px (collapsed by default)
```

**Mobile Layout (≤767px, Single Column):**
```
Priority-based stacking order:
1. Real-time Activity (height 120px)
2. Performance Metrics (height 100px)  
3. Turn Pipeline Status (height 120px)
4. World State Map (height 250px)
5. Character Networks (height 220px)
6. Event Cascade Flow (height 200px)  
7. Narrative Timeline (height 160px)
8. Analytics (collapsed, expandable)
```

### 1.4 Layout Hierarchy & Visual Weight

**Primary Focus (Large Tiles)**:
- **World State Map** (largest) - Central spatial context
- **Character Networks** - Key relationship visualization
- **Narrative Arc Timeline** - Temporal story progression

**Secondary Focus (Medium Tiles)**:
- **Event Cascade Flow** - Cause-and-effect relationships
- **Turn Pipeline Status** - System orchestration health
- **Real-time Activity** - Current narrative events

**Supporting Elements (Small Tiles)**:
- **Performance Metrics** - System health indicators
- **Quick Actions** - Contextual controls
- **Analytics Dashboard** - Deep analytical insights (collapsible)

---

## 2. Component Breakdown by Bento Box

### 2.A World State Map (Primary Tile)
**Grid Position**: Desktop cols 1-6, Mobile full-width
**Dimensions**: 592px × 320px (desktop)

**Purpose**: Interactive 3D spatial visualization of the Novel Engine world with real-time entity positions, movement trails, and activity hotspots.

**Content Structure**:
```
Header Zone (Height: 40px):
├── "World State: [World Name]" (H3 title)
├── Time Display: "Turn 1,247 | Day 52, 14:35"
└── View Controls: [2D/3D Toggle] [Fullscreen] [Settings]

Map Canvas (Height: 240px):
├── 3D Spatial Grid (10,000+ entity capacity)
├── Entity Markers:
│   ├── Characters (dynamic colored dots)
│   ├── NPCs (smaller neutral dots)
│   ├── Points of Interest (landmark icons)
│   └── Active Events (pulsing indicators)
├── Movement Trails (ghosted paths, 5-turn history)
├── Activity Heat Zones (colored overlays)
└── Environmental Effects (weather, lighting)

Footer Zone (Height: 40px):
├── Entity Count: "Characters: 12 | NPCs: 847 | Events: 3"
├── Zoom Level: "1:500 scale"
└── Coordinates Display on hover
```

**Interactive Features**:
- Pan/zoom with mouse/touch
- Click entity for details popover
- Hover for quick info tooltip
- Time scrubber integration
- Filter toggle for entity types

### 2.B Real-time Activity (Secondary Tile)  
**Grid Position**: Desktop cols 7-10, height 160px
**Dimensions**: 352px × 160px

**Purpose**: Live feed of current narrative events, turn execution status, and emerging story beats.

**Content Structure**:
```
Header (Height: 32px):
├── "Live Activity" (H4)
├── Status Indicator: ●LIVE (green pulse)
└── Pause/Play Controls

Activity Stream (Height: 96px):
├── Event Items (scrollable list):
│   ├── Timestamp (relative: "2s ago")
│   ├── Event Type Icon
│   ├── Brief Description (truncated)
│   └── Severity/Priority Color Bar
│
├── Event Types:
│   ├── Turn Started/Completed
│   ├── Character Action Performed
│   ├── Negotiation Initiated/Resolved
│   ├── World State Changed
│   └── Narrative Beat Generated

Footer (Height: 32px):
├── Event Rate: "3.2 events/min"
└── [View Full Log] Button
```

**Real-time Updates**:
- WebSocket connection for live events
- Auto-scroll with pause capability
- Expandable details on click
- Filterable by event type/character

### 2.C Performance Metrics (Supporting Tile)
**Grid Position**: Desktop cols 11-12, height 160px  
**Dimensions**: 176px × 160px

**Purpose**: System health monitoring and turn orchestration performance indicators.

**Content Structure**:
```
Header (Height: 24px):
└── "System Health" (H5)

Metrics Grid (Height: 104px):
├── CPU Usage: 67% (progress bar + number)
├── Memory: 4.2GB/8GB (progress bar)
├── Turn Latency: 1.2s avg (trend sparkline)
├── Active Sessions: 3 (number badge)
├── Event Queue: 47 pending (number + status)
└── AI API Calls: 12/min (rate display)

Footer (Height: 32px):
├── Overall Health: ● GREEN
└── [Details] Link
```

**Visual Indicators**:
- Color-coded health status (Green/Yellow/Red)
- Mini sparklines for trending metrics
- Progress bars for capacity metrics
- Alert badges for critical issues

### 2.D Turn Pipeline Status (Secondary Tile)
**Grid Position**: Desktop cols 7-10, height 160px
**Dimensions**: 352px × 160px

**Purpose**: Current turn orchestration pipeline progress across all 5 phases with execution details.

**Content Structure**:
```
Header (Height: 32px):
├── "Turn Pipeline" (H4)
├── Current Turn: #1,247
└── Status: "Phase 3/5 - Interaction Orchestration"

Pipeline Visualization (Height: 96px):
├── Phase Progress Bar (5 segments):
│   ├── Phase 1: World Update ✓ (completed, green)
│   ├── Phase 2: Subjective Brief ✓ (completed, green)  
│   ├── Phase 3: Interaction Orchestration ⟳ (active, blue)
│   ├── Phase 4: Event Integration ○ (pending, gray)
│   └── Phase 5: Narrative Integration ○ (pending, gray)
│
├── Active Phase Details:
│   ├── "Processing 3 negotiations"
│   ├── "2 characters, 1 mediator"
│   └── Estimated completion: "30s"

Footer (Height: 32px):
├── Turn Duration: "2.1s elapsed"
└── Phases Completed: "2/5"
```

**Progress Indicators**:
- Phase completion checkmarks
- Active phase spinner animation
- Time estimates for remaining phases
- Error indicators for failed phases

### 2.E Quick Actions (Supporting Tile)
**Grid Position**: Desktop cols 11-12, height 160px
**Dimensions**: 176px × 160px  

**Purpose**: Contextual controls and quick access functions for dashboard interaction.

**Content Structure**:
```
Header (Height: 24px):
└── "Controls" (H5)

Action Buttons (Height: 104px):
├── [Pause Simulation] (primary button)
├── [Export Data] (secondary button)
├── [Reset Filters] (secondary button)  
├── [Take Screenshot] (secondary button)
└── [Emergency Stop] (danger button)

Footer (Height: 32px):
├── Auto-Refresh: ON (toggle)
└── [Settings] Gear Icon
```

**Button States**:
- Primary: High contrast, action-oriented
- Secondary: Medium contrast, supportive
- Danger: Red styling, confirmation required
- Disabled: Low contrast, not interactive

### 2.F Character Networks (Primary Tile)
**Grid Position**: Desktop cols 1-6, height 280px
**Dimensions**: 592px × 280px

**Purpose**: Social network graph visualization showing character relationships, influence patterns, and interaction histories.

**Content Structure**:
```
Header Zone (Height: 40px):
├── "Character Networks" (H3)
├── Active Characters: 12
├── View Mode: [Relationship] [Influence] [Activity] (tabs)
└── Layout: [Force] [Circular] [Hierarchical] (dropdown)

Graph Canvas (Height: 200px):
├── Character Nodes:
│   ├── Size based on influence/activity level
│   ├── Color based on faction/role
│   ├── Character avatar thumbnails
│   └── Health/status ring indicators
│
├── Connection Edges:
│   ├── Line thickness = relationship strength
│   ├── Color = relationship type (ally/neutral/rival)
│   ├── Animated flow = recent interactions
│   └── Dashed lines = indirect connections
│
├── Interactive Features:
│   ├── Drag nodes to adjust layout
│   ├── Hover for relationship details
│   ├── Click for character details panel
│   └── Multi-select for comparison

Footer Zone (Height: 40px):
├── Filter Controls: [Show NPCs] [Hide Inactive] [Minimum Strength]
├── Legend: ● Ally ● Neutral ● Rival
└── [Analyze Clusters] [Export Network] buttons
```

**Network Metrics**:
- Node centrality calculations
- Community detection algorithms
- Relationship strength scoring
- Influence propagation tracking

### 2.G Event Cascade Flow (Secondary Tile)
**Grid Position**: Desktop cols 7-12, height 280px  
**Dimensions**: 592px × 280px

**Purpose**: Causal chain visualization showing how events trigger subsequent events across the narrative system.

**Content Structure**:
```
Header Zone (Height: 40px):
├── "Event Cascade Analysis" (H3)
├── Time Range: [Last 10 Turns] (dropdown)
└── Flow Direction: [Top-Down] [Left-Right] (toggle)

Flow Diagram (Height: 200px):
├── Event Nodes:
│   ├── Primary Events (large circles):
│   │   ├── Character Actions
│   │   ├── World Changes  
│   │   ├── Negotiation Outcomes
│   │   └── Environmental Effects
│   │
│   ├── Secondary Events (medium circles):
│   │   ├── Character Reactions
│   │   ├── Relationship Changes
│   │   └── State Updates
│   │
│   └── Tertiary Events (small circles):
│       ├── Ripple Effects
│       ├── Narrative Implications
│       └── Long-term Consequences
│
├── Causal Arrows:
│   ├── Solid arrows = direct causation
│   ├── Dashed arrows = probable causation  
│   ├── Color intensity = causation strength
│   └── Animation flow = temporal sequence
│
├── Cascade Metrics:
│   ├── Cascade Depth (max levels)
│   ├── Branching Factor (avg outcomes per event)
│   ├── Narrative Impact Score
│   └── Convergence Points (where chains merge)

Footer Zone (Height: 40px):
├── Complexity Score: 7.3/10
├── Active Cascades: 4  
└── [Trace Event] [Export Chains] buttons
```

**Analysis Features**:
- Interactive node expansion
- Path tracing between events
- Impact scoring algorithms
- Temporal filtering controls

### 2.H Narrative Arc Timeline (Primary Tile)
**Grid Position**: Desktop cols 1-12, height 200px
**Dimensions**: 1200px × 200px (full width)

**Purpose**: Horizontal timeline visualization of story progression, plot points, character arcs, and narrative quality metrics over time.

**Content Structure**:
```
Header Zone (Height: 32px):
├── "Narrative Arc Progression" (H3)
├── Arc Count: 7 Active, 3 Completed
└── Time Scale: [Turns] [Days] [Sessions] (toggle)

Timeline Canvas (Height: 136px):
├── Time Axis (bottom, 24px):
│   ├── Graduated scale markings
│   ├── Major markers (session boundaries)
│   ├── Current position indicator (red line)
│   └── Scrubber controls for navigation
│
├── Arc Swim Lanes (112px):
│   ├── Lane 1: "The Lost Artifact" (Completed)
│   │   ├── Plot points as diamonds (sized by importance)
│   │   ├── Character involvement bands
│   │   ├── Quality score trend line (0-10 scale)
│   │   └── Completion percentage
│   │
│   ├── Lane 2: "Political Intrigue" (Active)
│   │   ├── Current plot points
│   │   ├── Predicted trajectory (dashed)
│   │   ├── Character engagement levels
│   │   └── Conflict intensity markers
│   │
│   ├── Lane 3: "Character Romance" (Active)
│   ├── Lane 4: "Economic Crisis" (Emerging)
│   └── [Show/Hide More] (expandable lanes)
│
├── Cross-Arc Connections:
│   ├── Dotted lines between related plot points
│   ├── Character movement between arcs
│   └── Thematic resonance indicators

Footer Zone (Height: 32px):
├── Overall Narrative Health: 8.2/10
├── Pacing Score: Good
├── Thematic Consistency: 85%
└── [Arc Details] [Export Timeline] buttons
```

**Timeline Interactions**:
- Scrubber for temporal navigation
- Zoom in/out for different time scales
- Click plot points for detailed information
- Drag to select time ranges for analysis

### 2.I Analytics Dashboard (Supporting Tile - Collapsible)
**Grid Position**: Desktop cols 1-12, height 240px
**Dimensions**: 1200px × 240px (full width)

**Purpose**: Advanced analytical insights, predictive modeling, and deep narrative intelligence derived from pattern analysis.

**Content Structure**:
```
Header Zone (Height: 40px):
├── "Advanced Analytics" (H3)
├── [Collapse/Expand] Toggle (chevron icon)
├── Analysis Period: [Last 24 Hours] (dropdown)
└── [Refresh Analysis] [Export Report] buttons

Analytics Grid (Height: 160px) - 4 Equal Columns:

Column 1 - Narrative Quality:
├── "Story Health Metrics"
├── Coherence Score: 87% (progress ring)
├── Pacing Quality: Good (badge)  
├── Character Development: 8.1/10 (score)
├── Plot Progression Rate: +12% (trend)
└── Thematic Consistency: 91% (progress bar)

Column 2 - Predictive Insights:
├── "Narrative Predictions" 
├── Likely Plot Development: "Conflict escalation"
├── Character Arc Projections:
│   ├── Hero's Journey: 67% complete
│   ├── Romance Arc: 23% complete
│   └── Villain Arc: 89% complete
├── Estimated Session End: 2.3 hours
└── Story Satisfaction Forecast: 8.4/10

Column 3 - Performance Intelligence:
├── "System Optimization"
├── Computational Complexity: Medium
├── AI Usage Efficiency: 94%
├── Resource Bottlenecks: None
├── Turn Optimization Score: A+
└── Cost per Narrative Beat: $0.03

Column 4 - Engagement Metrics:
├── "Player/Character Engagement"
├── Character Activity Levels:
│   ├── High: 4 characters
│   ├── Medium: 6 characters  
│   └── Low: 2 characters
├── Social Network Density: 73%
├── Conflict Resolution Rate: 89%
└── Narrative Participation: 96%

Footer Zone (Height: 40px):
├── Last Updated: 2 minutes ago
├── Confidence Level: 92%
└── [Detailed Report] [Configure Metrics] links
```

**Analytics Features**:
- Machine learning predictions
- Statistical trend analysis
- Comparative benchmarking
- Customizable metric selection

---

## 3. Interaction Design & Cross-Filtering

### 3.1 Global Interaction Patterns

**Universal Behaviors**:
- **Hover States**: All interactive elements show subtle highlight (opacity: 0.8, scale: 1.02)
- **Loading States**: Animated skeleton placeholders during data updates
- **Error States**: Red border with error message overlay
- **Empty States**: Centered message with contextual actions

**Real-time Updates**:
- **WebSocket Connection**: Maintains persistent connection for live data
- **Update Frequency**: 1-2 second refresh rate for critical metrics
- **Visual Indicators**: Pulsing dot shows live connection status
- **Graceful Degradation**: Falls back to 5-second polling if WebSocket fails

### 3.2 Cross-Component Filtering System

**Master Filter State Management**:
```
FilterState: {
  timeRange: { start: Date, end: Date },
  selectedCharacters: Set<UUID>,
  selectedNarrativeArcs: Set<string>,
  activeContexts: Set<string>,
  eventTypes: Set<string>,
  spatialBounds: { minX, maxX, minY, maxY }
}
```

**Cross-Filtering Behaviors**:

#### A → B,C,D,E (World State Map affects other components)
- **Character Selection**: Click character on map → filter all components to that character
- **Area Selection**: Draw rectangle on map → filter by spatial bounds
- **Time Scrubbing**: Drag time slider → update all components to selected time
- **Visual Feedback**: Selected entities glow with blue outline, unselected fade to 30% opacity

#### B → A,F,G,H (Real-time Activity affects spatial and narrative components)  
- **Event Click**: Click event → highlight related entities on World Map
- **Character Filter**: Click character name → isolate their activities across dashboard
- **Event Type Filter**: Click event icon → filter all components by event type
- **Temporal Context**: Events older than selection fade to 60% opacity

#### F → A,G,H (Character Networks affects narrative flow)
- **Character Node Selection**: Click character → highlight all their interactions and narrative involvement
- **Relationship Path**: Click connection edge → show interaction history in Event Cascade
- **Cluster Analysis**: Select character group → filter narrative components to group activities
- **Influence Propagation**: Double-click node → animate influence ripples across other components

#### H → A,B,G,I (Narrative Arc Timeline affects temporal context)
- **Arc Selection**: Click narrative arc → filter all components to arc participants and timeline
- **Plot Point Focus**: Click plot point → jump to specific sequence in all temporal components
- **Time Range Brush**: Drag timeline selection → update all components to time window
- **Arc Comparison**: Multi-select arcs → show overlapping characters and events

### 3.3 Component-Specific Interactions

#### World State Map (A)
**Primary Interactions**:
```
Pan/Zoom: Mouse drag + scroll wheel
Entity Selection: Single click → details popover, double click → filter all
Multi-Select: Ctrl+drag rectangle → select multiple entities
Measurement Tool: Alt+click → distance/area measurement mode
Temporal Scrubber: Bottom timeline slider → time navigation

Hover Behaviors:
- Entity: Tooltip with name, type, last activity
- Path Trail: Show movement speed and direction
- Heat Zone: Display activity intensity and contributing factors

Click Behaviors:
- Character: → Focus across all components + character detail modal
- Location: → Spatial context menu with available actions
- Event Marker: → Event details popover + cascade visualization
- Empty Space: → Clear all selections, reset to global view
```

#### Real-time Activity (B)  
**Stream Interactions**:
```
Auto-Scroll: Default enabled, pause on user interaction
Manual Navigation: Scroll wheel to browse history
Event Actions: Right-click event → context menu (details, filter, trace)
Playback Controls: Play/pause, speed adjustment (0.5x to 4x)

Hover Behaviors:
- Event Item: Expand to show full details
- Character Name: Highlight related characters in other components
- Timestamp: Show relative time and absolute time

Click Behaviors:
- Event: → Filter dashboard + open event detail panel
- Character: → Character focus mode across all components
- Category Icon: → Filter by event category
- Severity Bar: → Sort by severity level
```

#### Performance Metrics (C)
**Health Monitoring**:
```
Metric Thresholds: Color-coded alerts (Green/Yellow/Red zones)
Historical Trends: Hover metric → sparkline with 24h history
Drill-Down: Click metric → detailed performance modal
Alert Management: Click alert badge → alert center with actions

Hover Behaviors:
- Progress Bar: Show precise values and historical comparison
- Status Indicator: Show last change time and trend direction
- Resource Usage: Show resource allocation and available capacity

Click Behaviors:
- Health Status: → System health dashboard
- Resource Metric: → Resource allocation panel
- Alert Badge: → Alert management interface
```

#### Character Networks (F)
**Graph Interactions**:
```
Node Manipulation: Drag nodes to adjust layout
Zoom/Pan: Mouse wheel + drag for graph navigation
Selection: Single/multi-select with Ctrl
Layout Algorithms: Toggle between force, circular, hierarchical

Force-Directed Physics:
- Attraction: Strong relationships pull nodes closer
- Repulsion: Unrelated characters push apart
- Stabilization: Graph settles into optimal layout

Hover Behaviors:
- Character Node: Highlight direct connections + relationship strength
- Connection Edge: Show relationship type, strength, recent interactions
- Empty Space: Show graph statistics and layout controls

Click Behaviors:
- Character Node: → Focus mode + character analysis panel
- Connection Edge: → Relationship history + interaction timeline
- Cluster Group: → Group analysis modal with shared characteristics
- Layout Button: → Apply new layout algorithm with animation
```

#### Event Cascade Flow (G)
**Causal Chain Navigation**:
```
Flow Tracing: Click event → highlight causal chain paths
Impact Analysis: Double-click event → show all downstream effects
Temporal Filtering: Time range slider affects displayed cascades
Complexity Controls: Simplify/expand view based on cascade depth

Interactive Elements:
- Event Nodes: Expandable for detailed context
- Causal Arrows: Clickable to show causation evidence
- Branch Points: Show alternative outcome paths
- Convergence Points: Highlight where chains merge

Hover Behaviors:
- Event Node: Show event details, participants, timestamps
- Causal Arrow: Display causation strength and evidence type
- Branch Point: Show probability of different outcomes

Click Behaviors:
- Event Node: → Event detail panel + causal analysis
- Causal Path: → Path analysis with probability calculations
- Branch Point: → Alternative outcome explorer
- Convergence: → Multi-event impact analysis
```

#### Narrative Arc Timeline (H)
**Temporal Navigation**:
```
Time Scrubbing: Drag scrubber to navigate through story time
Arc Expansion: Click arc name → expand to show detailed plot points
Plot Point Details: Click plot point → context panel with scene details
Arc Comparison: Multi-select for side-by-side comparison

Timeline Controls:
- Zoom: In/out for different time scales (minutes/hours/days)
- Playback: Animate through narrative progression
- Bookmark: Mark important plot points for quick access
- Export: Save timeline segment for external analysis

Hover Behaviors:
- Plot Point: Preview scene description and participants
- Arc Segment: Show narrative quality metrics for time period
- Character Band: Display character involvement intensity
- Quality Line: Show specific quality factors and scores

Click Behaviors:
- Plot Point: → Scene detail modal + character state at time
- Arc Lane: → Arc analysis panel with quality metrics
- Character Band: → Character's narrative journey view
- Time Marker: → Temporal context across all components
```

### 3.4 Modal and Panel System

**Panel Types**:
- **Detail Panels**: Slide-in from right (400px width)
- **Analysis Modals**: Center overlay with backdrop (800px width)
- **Context Menus**: Floating near cursor (max 200px width)
- **Tooltips**: Small informational overlays (max 300px width)

**Panel Management**:
```
Stack Management: Maximum 3 panels open simultaneously
Auto-Close: Panels close when related entity deselected
Persistence: Panel state maintained during navigation
Responsive: Panels collapse to bottom sheets on mobile
```

### 3.5 Keyboard Navigation & Accessibility

**Keyboard Shortcuts**:
```
Navigation:
- Tab: Cycle through interactive elements
- Shift+Tab: Reverse cycle
- Enter/Space: Activate focused element
- Escape: Close modals/panels, clear selections

Filtering:
- Ctrl+F: Open global filter panel
- Ctrl+C: Focus on character filter
- Ctrl+T: Focus on time range selector
- Ctrl+R: Reset all filters

View Control:
- Ctrl+Z: Undo last filter action  
- Ctrl+Y: Redo filter action
- F: Toggle fullscreen mode
- G: Toggle grid guidelines
```

**Accessibility Features**:
- **WCAG 2.1 AA Compliance**: Color contrast ratio ≥4.5:1
- **Screen Reader Support**: Comprehensive ARIA labels and descriptions
- **Focus Management**: Visible focus indicators, logical tab order
- **Alternative Text**: All visual elements have text alternatives
- **Reduced Motion**: Respects user's motion sensitivity preferences

### 3.6 State Persistence & Session Management

**Session State**:
```
UserSession: {
  filterPreferences: FilterState,
  viewConfiguration: { layout, componentStates },
  bookmarks: Array<{ name, timestamp, filters }>,
  customLayouts: Array<GridLayout>,
  recentActions: Array<UserAction>,
  preferences: UserPreferences
}
```

**Auto-Save Behavior**:
- **Filter State**: Saved every 2 seconds during active use
- **View Configuration**: Saved on layout changes
- **Session Restore**: Automatic restoration on browser refresh
- **Cross-Session**: Preferences persist across login sessions

**Bookmark System**:
- **Quick Bookmarks**: Save current dashboard state with one click
- **Named Bookmarks**: Custom names for important configurations
- **Shared Bookmarks**: Team sharing for collaborative analysis
- **Bookmark Management**: Organize, edit, and delete saved states

---

## 4. Visual Style Guide

### 4.1 Typography System

**Primary Font Stack**:
```css
/* Primary: Modern sans-serif for UI */
--font-primary: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;

/* Monospace: Code and data display */
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', 'Monaco', 'Consolas', monospace;

/* Accent: Distinctive headings */
--font-accent: 'Inter Display', 'Inter', system-ui, sans-serif;
```

**Typography Scale**:
```css
/* Headings */
--text-h1: 2.5rem/1.2 var(--font-accent); /* 40px, Dashboard title */
--text-h2: 2rem/1.3 var(--font-accent);   /* 32px, Section headers */
--text-h3: 1.5rem/1.4 var(--font-accent); /* 24px, Component titles */
--text-h4: 1.25rem/1.4 var(--font-primary); /* 20px, Subsection titles */
--text-h5: 1.125rem/1.4 var(--font-primary); /* 18px, Widget headers */

/* Body Text */
--text-base: 1rem/1.5 var(--font-primary);    /* 16px, Standard body */
--text-sm: 0.875rem/1.4 var(--font-primary);  /* 14px, Secondary info */
--text-xs: 0.75rem/1.3 var(--font-primary);   /* 12px, Captions */

/* Data/Code */
--text-mono: 0.875rem/1.4 var(--font-mono);   /* 14px, Data display */
--text-mono-xs: 0.75rem/1.3 var(--font-mono); /* 12px, Small data */

/* Weights */
--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

### 4.2 Color Palette

**Base Colors** (Dark Theme Primary):
```css
/* Neutrals - Primary Background Palette */
--color-bg-primary: #0a0a0b;     /* Main dashboard background */
--color-bg-secondary: #111113;   /* Bento box backgrounds */
--color-bg-tertiary: #1a1a1d;    /* Panel backgrounds */
--color-bg-elevated: #232328;    /* Modal/dropdown backgrounds */
--color-bg-overlay: rgba(10, 10, 11, 0.9); /* Backdrop overlays */

/* Neutrals - Border & Separator Palette */
--color-border-primary: #2a2a30;   /* Main borders */
--color-border-secondary: #3a3a42; /* Interactive borders */
--color-border-focus: #4a9eff;     /* Focus indicators */

/* Neutrals - Text Palette */
--color-text-primary: #f0f0f2;     /* Main text */
--color-text-secondary: #b0b0b8;   /* Secondary text */
--color-text-tertiary: #808088;    /* Muted text */
--color-text-inverse: #0a0a0b;     /* Text on light backgrounds */
```

**Semantic Colors**:
```css
/* Status Colors */
--color-success: #10b981;     /* Success states, positive metrics */
--color-success-bg: #064e3b;  /* Success background */
--color-success-border: #065f46; /* Success borders */

--color-warning: #f59e0b;     /* Warning states, attention needed */
--color-warning-bg: #78350f;  /* Warning background */
--color-warning-border: #92400e; /* Warning borders */

--color-error: #ef4444;       /* Error states, critical issues */
--color-error-bg: #7f1d1d;    /* Error background */
--color-error-border: #991b1b; /* Error borders */

--color-info: #3b82f6;        /* Info states, neutral information */
--color-info-bg: #1e3a8a;     /* Info background */
--color-info-border: #1e40af; /* Info borders */
```

**Functional Colors**:
```css
/* Primary Brand */
--color-primary: #6366f1;       /* Primary actions, key elements */
--color-primary-hover: #5b5fc7; /* Primary hover state */
--color-primary-active: #524fb7; /* Primary active state */
--color-primary-bg: #1e1b4b;    /* Primary background */

/* Secondary Actions */
--color-secondary: #64748b;     /* Secondary actions */
--color-secondary-hover: #475569; /* Secondary hover */
--color-secondary-active: #334155; /* Secondary active */

/* Interactive Elements */
--color-interactive: #06b6d4;   /* Links, interactive text */
--color-interactive-hover: #0891b2; /* Interactive hover */
```

**Data Visualization Colors**:
```css
/* Character/Entity Colors */
--color-character-1: #8b5cf6;  /* Purple - Primary characters */
--color-character-2: #06b6d4;  /* Cyan - Supporting characters */
--color-character-3: #10b981;  /* Green - Neutral characters */
--color-character-4: #f59e0b;  /* Amber - NPCs */
--color-character-5: #ef4444;  /* Red - Antagonists */
--color-character-6: #ec4899;  /* Pink - Special roles */

/* Narrative Arc Colors */
--color-arc-main: #6366f1;      /* Main story arc */
--color-arc-subplot: #8b5cf6;   /* Subplot arcs */
--color-arc-character: #06b6d4; /* Character development arcs */
--color-arc-romance: #ec4899;   /* Romance arcs */
--color-arc-conflict: #ef4444;  /* Conflict arcs */

/* Event Type Colors */
--color-event-action: #10b981;     /* Character actions */
--color-event-dialogue: #3b82f6;   /* Conversations */
--color-event-conflict: #ef4444;   /* Conflicts */
--color-event-discovery: #f59e0b;  /* Discoveries */
--color-event-world: #64748b;      /* World changes */
```

### 4.3 Spacing & Layout System

**Spacing Scale** (8px base unit):
```css
--space-0: 0;       /* 0px */
--space-1: 0.25rem; /* 4px */
--space-2: 0.5rem;  /* 8px - Base unit */
--space-3: 0.75rem; /* 12px */
--space-4: 1rem;    /* 16px */
--space-5: 1.25rem; /* 20px */
--space-6: 1.5rem;  /* 24px */
--space-8: 2rem;    /* 32px */
--space-10: 2.5rem; /* 40px */
--space-12: 3rem;   /* 48px */
--space-16: 4rem;   /* 64px */
--space-20: 5rem;   /* 80px */
--space-24: 6rem;   /* 96px */
```

**Grid System**:
```css
/* Grid Layout */
--grid-columns-desktop: 12;
--grid-columns-tablet: 8;
--grid-columns-mobile: 1;

--grid-gap-desktop: 24px;
--grid-gap-tablet: 20px;
--grid-gap-mobile: 16px;

--container-max-width: 1200px;
--container-padding: var(--space-6);
```

**Border Radius Scale**:
```css
--radius-xs: 0.125rem; /* 2px - Small elements */
--radius-sm: 0.25rem;  /* 4px - Buttons, inputs */
--radius-md: 0.375rem; /* 6px - Cards, panels */
--radius-lg: 0.5rem;   /* 8px - Large cards */
--radius-xl: 0.75rem;  /* 12px - Modals */
--radius-2xl: 1rem;    /* 16px - Hero elements */
--radius-full: 9999px; /* Circles, pills */
```

### 4.4 Component Styling

**Bento Box Base Styles**:
```css
.bento-box {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  transition: all 0.2s ease;
}

.bento-box:hover {
  border-color: var(--color-border-secondary);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
}

.bento-box-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-primary);
}

.bento-box-title {
  font: var(--text-h4);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
}
```

**Button System**:
```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-sm);
  font: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
  transition: all 0.15s ease;
  border: 1px solid transparent;
  cursor: pointer;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border-color: var(--color-border-secondary);
}

.btn-secondary:hover {
  background: var(--color-bg-elevated);
  border-color: var(--color-border-focus);
}

.btn-danger {
  background: var(--color-error);
  color: white;
  border-color: var(--color-error);
}
```

**Input & Form Styles**:
```css
.form-input {
  width: 100%;
  padding: var(--space-3);
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  font: var(--text-base);
  transition: all 0.15s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-border-focus);
  box-shadow: 0 0 0 2px rgba(74, 158, 255, 0.2);
}

.form-input::placeholder {
  color: var(--color-text-tertiary);
}
```

**Status Indicators**:
```css
.status-indicator {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font: var(--text-xs);
  font-weight: var(--font-medium);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-success {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success-border);
}

.status-warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning-border);
}

.status-error {
  background: var(--color-error-bg);
  color: var(--color-error);
  border: 1px solid var(--color-error-border);
}
```

### 4.5 Animation & Transitions

**Transition Timing**:
```css
/* Standard Transitions */
--transition-fast: 0.1s ease;      /* Hover effects, focus */
--transition-standard: 0.15s ease; /* Button states, form inputs */
--transition-slow: 0.2s ease;      /* Panel transitions */
--transition-page: 0.3s ease;      /* Page/modal transitions */

/* Easing Functions */
--ease-out-cubic: cubic-bezier(0.33, 1, 0.68, 1);
--ease-in-out-cubic: cubic-bezier(0.65, 0, 0.35, 1);
--ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
```

**Animation Keyframes**:
```css
@keyframes pulse-live {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

@keyframes slide-in-right {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes fade-in-up {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes loading-skeleton {
  0% { background-position: -200px 0; }
  100% { background-position: calc(200px + 100%) 0; }
}
```

**Loading States**:
```css
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg-tertiary) 25%,
    var(--color-bg-elevated) 37%,
    var(--color-bg-tertiary) 63%
  );
  background-size: 400px 100%;
  animation: loading-skeleton 1.4s ease-in-out infinite;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-border-primary);
  border-top: 2px solid var(--color-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
```

### 4.6 Responsive Design Tokens

**Breakpoints**:
```css
--breakpoint-mobile: 767px;
--breakpoint-tablet: 1439px;
--breakpoint-desktop: 1440px;

@media (max-width: 767px) {
  :root {
    --text-h1: 2rem/1.2 var(--font-accent);
    --text-h2: 1.75rem/1.3 var(--font-accent);
    --text-h3: 1.25rem/1.4 var(--font-accent);
    --container-padding: var(--space-4);
  }
}
```

**Component Responsive Behavior**:
```css
.bento-box {
  /* Desktop: 3D shadows and hover effects */
  @media (min-width: 1440px) {
    box-shadow: 
      0 1px 3px rgba(0, 0, 0, 0.3),
      0 1px 2px rgba(0, 0, 0, 0.2);
  }
  
  /* Tablet: Reduced spacing */
  @media (max-width: 1439px) and (min-width: 768px) {
    padding: var(--space-3);
  }
  
  /* Mobile: Full width, minimal padding */
  @media (max-width: 767px) {
    padding: var(--space-4);
    border-radius: var(--radius-md);
    margin-bottom: var(--space-4);
  }
}
```

### 4.7 Design Implementation Guidelines

**CSS Custom Properties Usage**:
```css
/* Component-specific properties */
.world-map {
  --map-height: 320px;
  --entity-size: 8px;
  --trail-opacity: 0.6;
  --zoom-min: 0.25;
  --zoom-max: 4.0;
}

.character-network {
  --node-size-min: 12px;
  --node-size-max: 32px;
  --edge-width-min: 1px;
  --edge-width-max: 4px;
  --force-strength: 0.3;
}

.timeline {
  --timeline-height: 200px;
  --scrubber-width: 2px;
  --arc-lane-height: 28px;
  --plot-point-size: 8px;
}
```

**Accessibility Compliance**:
```css
/* Focus indicators */
:focus-visible {
  outline: 2px solid var(--color-border-focus);
  outline-offset: 2px;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  :root {
    --color-bg-primary: #000000;
    --color-text-primary: #ffffff;
    --color-border-primary: #ffffff;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 5. Implementation Notes

### 5.1 Technical Requirements

**Frontend Framework**: React 18+ with TypeScript
**Styling**: CSS-in-JS (Styled Components or Emotion) + CSS Custom Properties
**State Management**: Redux Toolkit + RTK Query for API state
**Real-time**: WebSocket connection with socket.io-client
**Data Visualization**: D3.js for custom charts, Three.js for 3D world map
**Testing**: Jest + React Testing Library + Playwright for E2E

### 5.2 Performance Considerations

**Optimization Strategies**:
- Virtual scrolling for large lists (Real-time Activity, Analytics)
- Canvas rendering for high-entity-count World Map (>1000 entities)
- Debounced filter updates (300ms delay)
- Memoized expensive calculations (network analysis, cascade pathfinding)
- Progressive loading for historical data
- WebWorkers for complex data processing

**Bundle Size Targets**:
- Initial bundle: <500KB gzipped
- Vendor chunks: <300KB gzipped
- Async component chunks: <100KB each
- Critical CSS: <50KB inline

### 5.3 Development Workflow

**Component Structure**:
```
components/
├── BentoBox/           # Base bento box wrapper
├── WorldMap/          # 3D world state visualization
├── ActivityStream/    # Real-time event feed
├── MetricsPanel/      # Performance monitoring
├── NetworkGraph/      # Character relationship visualization
├── CascadeFlow/       # Event causation visualization
├── NarrativeTimeline/ # Story arc progression
└── AnalyticsDashboard/ # Advanced insights
```

**Design System Integration**:
- Shared design tokens file (`design-tokens.css`)
- Component library with Storybook documentation
- Automated visual regression testing
- Design-development handoff tools (Figma to code)

---

*This comprehensive UI Design Specification provides complete implementation guidance for the Novel Engine Emergent Narrative Dashboard. The specification balances Bento Grid aesthetic principles with complex dashboard functionality, ensuring both visual excellence and operational efficiency for monitoring emergent storytelling systems.*

**Implementation Ready**: This specification contains sufficient detail for independent frontend implementation without additional clarification. All visual, interaction, and technical requirements are defined with precise measurements, behaviors, and code examples.