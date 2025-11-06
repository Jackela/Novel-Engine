/**
 * Focus Trap Hook
 * TDD: Hook definition before tests (T016)
 * 
 * Constitution Alignment:
 * - Article II: Port interface (IFocusManager abstraction)
 * - Article V: SRP - Single responsibility (focus management)
 */

import { useEffect, useRef, type RefObject } from 'react'
import type { FocusTrapResult } from '../types/accessibility'

export interface IFocusManager {
  trapFocus: (containerRef: RefObject<HTMLElement>) => void
  restoreFocus: (previousElement?: HTMLElement | null) => void
  getFirstFocusable: (container: HTMLElement) => HTMLElement | null
  getLastFocusable: (container: HTMLElement) => HTMLElement | null
}

export interface UseFocusTrapOptions {
  enabled?: boolean
  restoreFocus?: boolean
  initialFocus?: HTMLElement | null
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR)).filter(
    (el): el is HTMLElement => el instanceof HTMLElement && !el.hasAttribute('disabled')
  )
}

export function useFocusTrap(
  containerRef: RefObject<HTMLElement>,
  options: UseFocusTrapOptions = {}
): FocusTrapResult {
  const { enabled = true, restoreFocus = true, initialFocus } = options
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const isActiveRef = useRef(false)

  const getFirstFocusable = (container: HTMLElement): HTMLElement | null => {
    const elements = getFocusableElements(container)
    return elements[0] || null
  }

  const getLastFocusable = (container: HTMLElement): HTMLElement | null => {
    const elements = getFocusableElements(container)
    return elements[elements.length - 1] || null
  }

  const handleTabKey = (event: KeyboardEvent) => {
    if (!containerRef.current || !enabled) return

    const focusableElements = getFocusableElements(containerRef.current)
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    if (event.shiftKey) {
      // Shift + Tab: Moving backward
      if (document.activeElement === firstElement) {
        event.preventDefault()
        lastElement?.focus()
      }
    } else {
      // Tab: Moving forward
      if (document.activeElement === lastElement) {
        event.preventDefault()
        firstElement?.focus()
      }
    }
  }

  const activate = () => {
    if (!containerRef.current || !enabled) return

    // Store current focus
    previousFocusRef.current = document.activeElement as HTMLElement

    // Set initial focus
    const focusTarget = initialFocus || getFirstFocusable(containerRef.current)
    focusTarget?.focus()

    isActiveRef.current = true
  }

  const deactivate = () => {
    if (restoreFocus && previousFocusRef.current) {
      previousFocusRef.current.focus()
      previousFocusRef.current = null
    }

    isActiveRef.current = false
  }

  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        handleTabKey(event)
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [enabled, containerRef])

  useEffect(() => {
    if (enabled && containerRef.current) {
      activate()
    }

    return () => {
      if (enabled) {
        deactivate()
      }
    }
  }, [enabled])

  return {
    activate,
    deactivate,
    isActive: isActiveRef.current,
  }
}
