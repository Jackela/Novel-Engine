/**
 * Accessibility TypeScript Type Definitions
 * WCAG 2.1 AA Compliance Types for Novel Engine Frontend
 * 
 * Constitution Alignment:
 * - Article III: TDD - Types defined before implementation
 * - Article V: SOLID - Interface Segregation Principle
 */

/**
 * ARIA role types for semantic HTML elements
 */
export type AriaRole =
  | 'button'
  | 'checkbox'
  | 'dialog'
  | 'link'
  | 'listbox'
  | 'menu'
  | 'menuitem'
  | 'option'
  | 'radio'
  | 'tab'
  | 'tabpanel'
  | 'textbox'
  | 'alert'
  | 'status'
  | 'progressbar'
  | 'region'
  | 'navigation'
  | 'main'
  | 'complementary'
  | 'banner'
  | 'contentinfo'

/**
 * ARIA live region politeness levels
 */
export type AriaLive = 'off' | 'polite' | 'assertive'

/**
 * Keyboard navigation key codes
 */
export enum KeyboardKey {
  Enter = 'Enter',
  Space = ' ',
  Escape = 'Escape',
  Tab = 'Tab',
  ArrowUp = 'ArrowUp',
  ArrowDown = 'ArrowDown',
  ArrowLeft = 'ArrowLeft',
  ArrowRight = 'ArrowRight',
  Home = 'Home',
  End = 'End',
}

/**
 * Focus management configuration
 */
export interface FocusConfig {
  /** Element to focus on mount */
  initialFocus?: HTMLElement | null
  /** Element to return focus to on unmount */
  returnFocus?: HTMLElement | null
  /** Trap focus within container */
  trapFocus?: boolean
  /** Restore focus on unmount */
  restoreFocus?: boolean
}

/**
 * Accessible component base props
 */
export interface AccessibleProps {
  /** ARIA label for screen readers */
  'aria-label'?: string
  /** ID of element that labels this element */
  'aria-labelledby'?: string
  /** ID of element that describes this element */
  'aria-describedby'?: string
  /** ARIA role override */
  role?: AriaRole
  /** Tab index for keyboard navigation */
  tabIndex?: number
}

/**
 * Keyboard navigation handler configuration
 */
export interface KeyboardNavConfig {
  /** Keys to handle */
  keys: KeyboardKey[]
  /** Handler function */
  onKeyDown: (event: React.KeyboardEvent, key: KeyboardKey) => void
  /** Prevent default browser behavior */
  preventDefault?: boolean
  /** Stop event propagation */
  stopPropagation?: boolean
}

/**
 * Screen reader announcement types
 */
export interface ScreenReaderAnnouncement {
  /** Message to announce */
  message: string
  /** Politeness level */
  politeness: AriaLive
  /** Clear previous announcements */
  clearPrevious?: boolean
}

/**
 * Loading state accessibility metadata
 */
export interface LoadingA11yMetadata {
  /** Loading state label */
  label: string
  /** Live region politeness */
  politeness: AriaLive
  /** Announce completion */
  announceCompletion?: boolean
  /** Completion message */
  completionMessage?: string
}

/**
 * Focus trap return value
 */
export interface FocusTrapResult {
  /** Activate focus trap */
  activate: () => void
  /** Deactivate focus trap */
  deactivate: () => void
  /** Check if trap is active */
  isActive: boolean
}

/**
 * IAccessibleComponent Interface (Port - Article II)
 * Base interface for all accessible React components
 * T011: Foundation interface for WCAG 2.1 AA compliance
 */
export interface IAccessibleComponent {
  /** Keyboard tab index (0 for focusable, -1 for not focusable) */
  tabIndex?: number
  /** Keyboard event handler */
  onKeyDown?: (event: React.KeyboardEvent) => void
  /** ARIA role override */
  role?: AriaRole
  /** ARIA label for screen readers */
  'aria-label'?: string
  /** ID of element that labels this component */
  'aria-labelledby'?: string
  /** ID of element that describes this component */
  'aria-describedby'?: string
  /** Ref to underlying DOM element */
  ref?: React.Ref<HTMLElement>
}

/**
 * IKeyboardHandler Interface (Port - Article II)
 * Abstract interface for keyboard navigation handling
 * T012: Foundation interface for keyboard interactions
 */
export interface IKeyboardHandler {
  handleEnterKey: (event: React.KeyboardEvent) => void
  handleSpaceKey: (event: React.KeyboardEvent) => void
  handleEscapeKey: (event: React.KeyboardEvent) => void
  handleArrowKeys: (event: React.KeyboardEvent, direction: 'up' | 'down' | 'left' | 'right') => void
}

/**
 * IFocusManager Interface (Port - Article II)
 * Abstract interface for focus management and trapping
 * T013: Foundation interface for focus control
 */
export interface IFocusManager {
  trapFocus: (containerRef: React.RefObject<HTMLElement>) => void
  restoreFocus: (previousElement?: HTMLElement | null) => void
  getFirstFocusable: (container: HTMLElement) => HTMLElement | null
  getLastFocusable: (container: HTMLElement) => HTMLElement | null
}

/**
 * IPerformanceMonitor Interface (Port - Article II)
 * Abstract interface for Web Vitals tracking and performance monitoring
 * T014: Foundation interface for observability (Article VII)
 */
export interface IPerformanceMonitor {
  trackWebVitals: () => void
  reportMetric: (metric: PerformanceMetric) => void
}

/**
 * Performance metric type for Web Vitals
 */
export interface PerformanceMetric {
  /** Metric name (LCP, FID, CLS, etc.) */
  name: string
  /** Metric value in milliseconds or score */
  value: number
  /** Performance rating */
  rating: 'good' | 'needs-improvement' | 'poor'
  /** Delta from previous measurement */
  delta?: number
  /** Unique metric ID */
  id?: string
}
