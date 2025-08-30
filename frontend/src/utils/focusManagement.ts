/**
 * Focus Management Utilities for Accessibility
 * ==========================================
 * 
 * Utilities for managing focus in modals, dialogs, and complex UI components
 * to ensure WCAG 2.1 AA compliance and excellent keyboard accessibility.
 */

interface FocusTrapOptions {
  onEscape?: () => void;
  preventScroll?: boolean;
  restoreFocus?: boolean;
  initialFocus?: HTMLElement | string;
}

interface FocusableElement {
  element: HTMLElement;
  tabIndex: number;
}

class FocusTrap {
  private container: HTMLElement;
  private previouslyFocused: Element | null;
  private focusableElements: NodeListOf<HTMLElement> | null = null;
  private options: FocusTrapOptions;
  private isActive = false;

  constructor(container: HTMLElement, options: FocusTrapOptions = {}) {
    this.container = container;
    this.options = options;
    this.previouslyFocused = document.activeElement;
  }

  /**
   * Get all focusable elements within the container
   */
  private getFocusableElements(): HTMLElement[] {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');

    const elements = this.container.querySelectorAll<HTMLElement>(focusableSelectors);
    return Array.from(elements).filter(el => {
      return el.offsetWidth > 0 && el.offsetHeight > 0 && 
             getComputedStyle(el).visibility !== 'hidden';
    });
  }

  /**
   * Handle keydown events for focus trapping
   */
  private handleKeyDown = (event: KeyboardEvent) => {
    if (!this.isActive) return;

    // Handle Escape key
    if (event.key === 'Escape' && this.options.onEscape) {
      event.preventDefault();
      this.options.onEscape();
      return;
    }

    // Handle Tab key for focus trapping
    if (event.key === 'Tab') {
      const focusableElements = this.getFocusableElements();
      
      if (focusableElements.length === 0) {
        event.preventDefault();
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];
      const currentElement = document.activeElement as HTMLElement;

      if (event.shiftKey) {
        // Shift + Tab (backward)
        if (currentElement === firstElement || !this.container.contains(currentElement)) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab (forward)
        if (currentElement === lastElement || !this.container.contains(currentElement)) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    }
  };

  /**
   * Activate the focus trap
   */
  activate(): void {
    if (this.isActive) return;

    this.isActive = true;
    document.addEventListener('keydown', this.handleKeyDown);

    // Focus initial element
    const focusableElements = this.getFocusableElements();
    if (focusableElements.length > 0) {
      const initialElement = this.options.initialFocus 
        ? (typeof this.options.initialFocus === 'string' 
           ? this.container.querySelector(this.options.initialFocus) as HTMLElement
           : this.options.initialFocus)
        : focusableElements[0];
      
      if (initialElement) {
        initialElement.focus({ preventScroll: this.options.preventScroll });
      }
    }
  }

  /**
   * Deactivate the focus trap and restore previous focus
   */
  deactivate(): void {
    if (!this.isActive) return;

    this.isActive = false;
    document.removeEventListener('keydown', this.handleKeyDown);

    // Restore focus to previously focused element
    if (this.options.restoreFocus !== false && this.previouslyFocused) {
      (this.previouslyFocused as HTMLElement).focus({ preventScroll: true });
    }
  }
}

/**
 * React hook for managing focus traps in modal components
 */
export const useFocusTrap = (
  isOpen: boolean,
  containerRef: React.RefObject<HTMLElement>,
  options: FocusTrapOptions = {}
) => {
  const focusTrapRef = React.useRef<FocusTrap | null>(null);

  React.useEffect(() => {
    if (!containerRef.current) return;

    if (isOpen) {
      // Create and activate focus trap
      focusTrapRef.current = new FocusTrap(containerRef.current, {
        restoreFocus: true,
        ...options,
      });
      focusTrapRef.current.activate();
    } else if (focusTrapRef.current) {
      // Deactivate focus trap
      focusTrapRef.current.deactivate();
      focusTrapRef.current = null;
    }

    // Cleanup on unmount
    return () => {
      if (focusTrapRef.current) {
        focusTrapRef.current.deactivate();
        focusTrapRef.current = null;
      }
    };
  }, [isOpen, containerRef, options]);
};

/**
 * Utility to announce content changes to screen readers
 */
export const announceToScreenReader = (
  message: string, 
  priority: 'polite' | 'assertive' = 'polite'
): void => {
  const announcer = document.createElement('div');
  announcer.setAttribute('aria-live', priority);
  announcer.setAttribute('aria-atomic', 'true');
  announcer.style.position = 'absolute';
  announcer.style.left = '-10000px';
  announcer.style.width = '1px';
  announcer.style.height = '1px';
  announcer.style.overflow = 'hidden';
  
  document.body.appendChild(announcer);
  announcer.textContent = message;
  
  // Remove after announcement
  setTimeout(() => {
    document.body.removeChild(announcer);
  }, 1000);
};

/**
 * Skip to element utility for skip links
 */
export const skipToElement = (elementId: string): void => {
  const element = document.getElementById(elementId);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    element.focus({ preventScroll: true });
  }
};

/**
 * Enhanced focus management for complex components
 */
export const manageFocus = {
  /**
   * Get all focusable elements within a container
   */
  getFocusableElements: (container: HTMLElement): HTMLElement[] => {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]',
    ].join(', ');

    return Array.from(container.querySelectorAll<HTMLElement>(focusableSelectors))
      .filter(el => {
        const style = getComputedStyle(el);
        return el.offsetWidth > 0 && el.offsetHeight > 0 && 
               style.visibility !== 'hidden' && style.display !== 'none';
      });
  },

  /**
   * Set focus to first focusable element in container
   */
  focusFirst: (container: HTMLElement): boolean => {
    const focusableElements = manageFocus.getFocusableElements(container);
    if (focusableElements.length > 0) {
      focusableElements[0].focus();
      return true;
    }
    return false;
  },

  /**
   * Set focus to last focusable element in container
   */
  focusLast: (container: HTMLElement): boolean => {
    const focusableElements = manageFocus.getFocusableElements(container);
    if (focusableElements.length > 0) {
      focusableElements[focusableElements.length - 1].focus();
      return true;
    }
    return false;
  },
};

export default { useFocusTrap, announceToScreenReader, skipToElement, manageFocus };