/**
 * Keyboard Navigation Hook
 * TDD: Hook definition before tests (T015)
 * 
 * Constitution Alignment:
 * - Article II: Port interface (IKeyboardHandler abstraction)
 * - Article V: SRP - Single responsibility (keyboard event handling)
 */

import { useCallback, type KeyboardEvent } from 'react'
import { KeyboardKey } from '@/types/accessibility'

export interface IKeyboardHandler {
  handleEnterKey: (event: KeyboardEvent) => void
  handleSpaceKey: (event: KeyboardEvent) => void
  handleEscapeKey: (event: KeyboardEvent) => void
  handleArrowKeys: (event: KeyboardEvent, direction: 'up' | 'down' | 'left' | 'right') => void
}

export interface UseKeyboardNavOptions {
  onEnter?: () => void
  onSpace?: () => void
  onEscape?: () => void
  onArrowUp?: () => void
  onArrowDown?: () => void
  onArrowLeft?: () => void
  onArrowRight?: () => void
  preventDefault?: boolean
  stopPropagation?: boolean
}

export function useKeyboardNav(options: UseKeyboardNavOptions = {}): IKeyboardHandler {
  const {
    onEnter,
    onSpace,
    onEscape,
    onArrowUp,
    onArrowDown,
    onArrowLeft,
    onArrowRight,
    preventDefault = false,
    stopPropagation = false,
  } = options

  const handleEnterKey = useCallback(
    (event: KeyboardEvent) => {
      if (preventDefault) event.preventDefault()
      if (stopPropagation) event.stopPropagation()
      onEnter?.()
    },
    [onEnter, preventDefault, stopPropagation]
  )

  const handleSpaceKey = useCallback(
    (event: KeyboardEvent) => {
      if (preventDefault) event.preventDefault()
      if (stopPropagation) event.stopPropagation()
      onSpace?.()
    },
    [onSpace, preventDefault, stopPropagation]
  )

  const handleEscapeKey = useCallback(
    (event: KeyboardEvent) => {
      if (preventDefault) event.preventDefault()
      if (stopPropagation) event.stopPropagation()
      onEscape?.()
    },
    [onEscape, preventDefault, stopPropagation]
  )

  const handleArrowKeys = useCallback(
    (event: KeyboardEvent, direction: 'up' | 'down' | 'left' | 'right') => {
      if (preventDefault) event.preventDefault()
      if (stopPropagation) event.stopPropagation()

      switch (direction) {
        case 'up':
          onArrowUp?.()
          break
        case 'down':
          onArrowDown?.()
          break
        case 'left':
          onArrowLeft?.()
          break
        case 'right':
          onArrowRight?.()
          break
      }
    },
    [onArrowUp, onArrowDown, onArrowLeft, onArrowRight, preventDefault, stopPropagation]
  )

  return {
    handleEnterKey,
    handleSpaceKey,
    handleEscapeKey,
    handleArrowKeys,
  }
}
