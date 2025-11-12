import { forwardRef } from 'react';
import type React from 'react';
import { IAccessibleComponent } from '../../types/accessibility';

type ReactKeyboardEvent = React.KeyboardEvent<HTMLDivElement>;

interface KeyboardButtonProps extends Partial<IAccessibleComponent> {
  onClick: () => void;
  children: React.ReactNode;
  className?: string;
  ariaLabel?: string;
  ariaPressed?: boolean;
  ariaExpanded?: boolean;
  disabled?: boolean;
  style?: React.CSSProperties;
}

export const KeyboardButton = forwardRef<HTMLDivElement, KeyboardButtonProps>(
  (
    {
      onClick,
      children,
      className = '',
      ariaLabel,
      ariaPressed,
      ariaExpanded,
      disabled = false,
      style,
      ...props
    },
    ref
  ) => {
    const handleKeyDown = (event: ReactKeyboardEvent) => {
      if (disabled) return;

      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        onClick();
      }

      if (props.onKeyDown) {
        props.onKeyDown(event as unknown as KeyboardEvent);
      }
    };

    const handleClick = () => {
      if (disabled) return;
      onClick();
    };

    return (
      <div
        ref={ref}
        role="button"
        tabIndex={disabled ? -1 : 0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        aria-label={ariaLabel}
        aria-pressed={ariaPressed}
        aria-expanded={ariaExpanded}
        aria-disabled={disabled}
        className={`keyboard-button ${className} ${disabled ? 'disabled' : ''}`}
        style={{
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.6 : 1,
          ...style,
        }}
      >
        {children}
      </div>
    );
  }
);

KeyboardButton.displayName = 'KeyboardButton';
