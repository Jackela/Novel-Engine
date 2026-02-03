# Novel Engine Design System

## Core Principles

- **Token-First**: No hardcoded colors, spacing, or font sizes. Use semantic tokens only.
- **Three Domains**: App Shell / Editor Canvas / Graph Canvas have distinct rules.
- **Orthogonal Theming**: Color mode (light/dark) and typography mode (default/literary) are independent.

---

## 1. Three Rendering Domains

| Domain | Scope | Font | Background | Purpose |
|--------|-------|------|------------|---------|
| **App Shell** | Navigation, sidebar, topbar, panels | `font-sans` | `bg-background` | SaaS-style UI |
| **Editor Canvas** | Tiptap editor, prose content | `font-serif` | `bg-paper` | Book-like reading/writing |
| **Graph Canvas** | React Flow nodes, edges | `font-sans` | `bg-weaver-canvas` | Technical visualization |

---

## 2. Color Tokens

### Semantic Colors
Use HSL variables: `hsl(var(--primary))`

| Token | Usage |
|-------|-------|
| `primary` | Primary actions, links |
| `secondary` | Secondary actions |
| `destructive` | Delete, danger |
| `warning` | Caution states |
| `success` | Positive feedback |
| `muted` | Disabled, subtle |
| `accent` | Highlights |

### Weaver-Specific Colors
For Graph Canvas only:

| Token | Value | Usage |
|-------|-------|-------|
| `weaver-canvas` | `rgb(10 11 15)` | Graph background |
| `weaver-surface` | `rgb(16 19 26)` | Node background |
| `weaver-border` | `rgb(32 38 56)` | Node borders |
| `weaver-glow` | `rgb(0 245 255)` | Active/selected state |
| `weaver-neon` | `rgb(176 38 255)` | Accent highlights |
| `weaver-loading` | `rgb(0 229 255)` | Loading state |
| `weaver-error` | `rgb(255 92 77)` | Error state |

### Literary Theme Tokens
For Editor Canvas in literary mode:

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--paper` | `40 30% 96%` | `30 15% 12%` | Editor background |
| `--ink` | `30 15% 20%` | `40 20% 85%` | Editor text |
| `--accent-literary` | `35 80% 45%` | `35 70% 55%` | Literary highlights |

---

## 3. Typography

### Font Stack

| Token | Font Family | Usage |
|-------|-------------|-------|
| `font-sans` | Manrope, system-ui | UI text, labels, buttons |
| `font-serif` | Lora, Georgia | Literary content in editor |
| `font-display` | Space Grotesk | Headings, titles |
| `font-mono` | IBM Plex Mono | Code, technical data |

### Type Scale

| Class | Size | Line Height | Usage |
|-------|------|-------------|-------|
| `text-xs` | 12px | 1.5 | Captions |
| `text-sm` | 14px | 1.5 | Secondary text |
| `text-base` | 16px | 1.5 | Body text |
| `text-lg` | 18px | 1.6 | Editor default |
| `text-xl` | 20px | 1.5 | Subheadings |
| `text-2xl` | 24px | 1.4 | Section titles |
| `text-3xl` | 30px | 1.3 | Page titles |

### Editor Typography (Literary Mode)
```css
.prose-editor {
  font-family: var(--font-serif);
  font-size: 1.125rem;    /* 18px */
  line-height: 1.75;
  max-width: 65ch;        /* Optimal reading width */
}
```

---

## 4. Spacing System

Use 4px grid. **No arbitrary pixel values.**

| Token | Value | Usage |
|-------|-------|-------|
| `space-1` | 4px | Tight gaps |
| `space-2` | 8px | Component internal |
| `space-3` | 12px | Small gaps |
| `space-4` | 16px | Standard gaps |
| `space-6` | 24px | Section gaps |
| `space-8` | 32px | Large gaps |

**Allowed Tailwind classes**: `p-1`, `p-2`, `p-4`, `gap-2`, `gap-4`, `space-y-4`, etc.

**Forbidden**: `margin: 13px`, `padding: 17px`, or any non-grid values.

---

## 5. Component Rules

### App Shell Components
- Use **only** shadcn/ui components from `@/components/ui/`
- Styling via Tailwind utilities
- Interactive states: `hover:`, `focus-visible:`, `active:`
- No custom CSS classes except for layout

### Editor Canvas Components
- Custom `.prose-editor` class for container
- Target `.ProseMirror` for editor-specific styles
- Character mentions: `.character-mention` class
- All styles in `src/styles/editor.css`

### Graph Canvas Components
- Base class: `.weaver-node`
- Status classes: `.node-idle`, `.node-active`, `.node-loading`, `.node-error`
- Use `data-node-type` attribute for type-specific styling
- All styles in `src/styles/tailwind.css` component layer

---

## 6. Theme Switching

### Color Mode (Light/Dark)
- Controlled by `class="dark"` on `<html>`
- Managed by `next-themes` package
- Affects all three domains

### Typography Mode (Default/Literary)
- Controlled by `data-typography="literary"` on `<html>`
- Managed by `TypographyToggle` component
- Affects **only** Editor Canvas

### Theme Matrix (4 Combinations)

```
                    default             literary
            ┌─────────────────┬─────────────────┐
    light   │ SaaS + sans     │ Paper + serif   │
            ├─────────────────┼─────────────────┤
    dark    │ Dark + sans     │ Warm dark+serif │
            └─────────────────┴─────────────────┘
```

---

## 7. Animation & Motion

### Timing
| Token | Duration | Usage |
|-------|----------|-------|
| `duration-fast` | 150ms | Micro-interactions |
| `duration-normal` | 300ms | Standard transitions |
| `duration-slow` | 500ms | Page transitions |

### Easing
- Use `ease-out` for entries
- Use `ease-in` for exits
- Use `ease-in-out` for state changes

### Reduced Motion
Always respect `prefers-reduced-motion`:
```css
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; }
}
```

---

## 8. Accessibility Requirements

- **Contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Focus**: All interactive elements must have visible `focus-visible` state
- **Keyboard**: Full keyboard navigation support
- **ARIA**: Use semantic HTML first, ARIA when necessary

---

## Quick Reference

### DO
- Use semantic color tokens: `bg-primary`, `text-muted-foreground`
- Use spacing tokens: `p-4`, `gap-6`, `space-y-2`
- Use font tokens: `font-sans`, `font-serif`
- Follow domain-specific rules

### DON'T
- Hardcode colors: `#ff0000`, `rgb(255, 0, 0)`
- Use arbitrary values: `margin: 13px`, `padding-top: 7px`
- Mix domain styles (e.g., weaver colors in editor)
- Create custom CSS classes for shadcn/ui components
