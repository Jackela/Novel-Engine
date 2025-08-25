/**
 * Magic Enhanced Badge Component
 * =============================
 * 
 * Versatile badge component with Magic UI patterns:
 * - Multiple variants and sizes
 * - Animated states
 * - Interactive capabilities
 * - Accessibility features
 */

import React, { forwardRef, HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 select-none",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80 shadow-sm",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80 shadow-sm",
        success:
          "border-transparent bg-green-500 text-white hover:bg-green-500/80 shadow-sm",
        warning:
          "border-transparent bg-yellow-500 text-white hover:bg-yellow-500/80 shadow-sm",
        info:
          "border-transparent bg-blue-500 text-white hover:bg-blue-500/80 shadow-sm",
        outline:
          "text-foreground border-border hover:bg-accent hover:text-accent-foreground",
        ghost:
          "border-transparent text-foreground hover:bg-accent hover:text-accent-foreground",
        gradient:
          "border-transparent bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-md hover:shadow-lg",
        glass:
          "border-border/50 bg-background/80 backdrop-blur-sm text-foreground hover:bg-background/90",
        dot:
          "border-transparent bg-background text-foreground relative pl-4 hover:bg-accent",
        pulse:
          "border-transparent bg-primary text-primary-foreground animate-pulse",
        glow:
          "border-transparent bg-primary text-primary-foreground shadow-[0_0_10px_rgba(59,130,246,0.5)]"
      },
      size: {
        sm: "text-xs px-2 py-0.5",
        default: "text-xs px-2.5 py-0.5",
        lg: "text-sm px-3 py-1",
        xl: "text-base px-4 py-1.5"
      },
      interactive: {
        true: "cursor-pointer transform hover:scale-105 active:scale-95",
        false: ""
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      interactive: false
    }
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  interactive?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  onRemove?: () => void;
  pulse?: boolean;
  count?: number;
}

const Badge = forwardRef<HTMLDivElement, BadgeProps>(
  ({
    className,
    variant,
    size,
    interactive,
    leftIcon,
    rightIcon,
    onRemove,
    pulse,
    count,
    children,
    onClick,
    ...props
  }, ref) => {
    const isInteractive = interactive || !!onClick || !!onRemove;

    return (
      <div
        ref={ref}
        className={cn(
          badgeVariants({ variant, size, interactive: isInteractive }),
          variant === 'dot' && 'before:content-[""] before:absolute before:left-1.5 before:top-1/2 before:-translate-y-1/2 before:w-1.5 before:h-1.5 before:bg-current before:rounded-full',
          pulse && 'animate-pulse',
          className
        )}
        onClick={onClick}
        role={isInteractive ? "button" : undefined}
        tabIndex={isInteractive ? 0 : undefined}
        {...props}
      >
        {leftIcon && (
          <span className="mr-1 flex items-center">
            {leftIcon}
          </span>
        )}

        <span className="flex items-center gap-1">
          {children}
          {count !== undefined && count > 0 && (
            <span className="ml-1 text-[10px] bg-current/20 rounded-full px-1.5 py-0.5 min-w-[16px] text-center">
              {count > 99 ? '99+' : count}
            </span>
          )}
        </span>

        {rightIcon && !onRemove && (
          <span className="ml-1 flex items-center">
            {rightIcon}
          </span>
        )}

        {onRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="ml-1 flex items-center hover:bg-current/20 rounded-full p-0.5 transition-colors"
            aria-label="Remove badge"
          >
            <svg
              className="w-3 h-3"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>
    );
  }
);

Badge.displayName = "Badge";

// Status Badge Component
interface StatusBadgeProps extends Omit<BadgeProps, 'variant'> {
  status: 'online' | 'offline' | 'idle' | 'busy' | 'away';
  showLabel?: boolean;
}

const StatusBadge = forwardRef<HTMLDivElement, StatusBadgeProps>(
  ({ status, showLabel = true, className, ...props }, ref) => {
    const statusConfig = {
      online: { 
        variant: 'success' as const, 
        label: 'Online',
        dot: 'bg-green-500'
      },
      offline: { 
        variant: 'secondary' as const, 
        label: 'Offline',
        dot: 'bg-gray-400'
      },
      idle: { 
        variant: 'warning' as const, 
        label: 'Idle',
        dot: 'bg-yellow-500'
      },
      busy: { 
        variant: 'destructive' as const, 
        label: 'Busy',
        dot: 'bg-red-500'
      },
      away: { 
        variant: 'info' as const, 
        label: 'Away',
        dot: 'bg-blue-500'
      }
    };

    const config = statusConfig[status];

    return (
      <Badge
        ref={ref}
        variant={config.variant}
        className={cn("gap-1.5", className)}
        {...props}
      >
        <div className={cn("w-2 h-2 rounded-full", config.dot)} />
        {showLabel && config.label}
      </Badge>
    );
  }
);

StatusBadge.displayName = "StatusBadge";

// Notification Badge Component
interface NotificationBadgeProps extends HTMLAttributes<HTMLDivElement> {
  count: number;
  max?: number;
  dot?: boolean;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
}

const NotificationBadge = forwardRef<HTMLDivElement, NotificationBadgeProps>(
  ({ count, max = 99, dot = false, position = 'top-right', className, children, ...props }, ref) => {
    const positionClasses = {
      'top-right': 'top-0 right-0 -translate-y-1/2 translate-x-1/2',
      'top-left': 'top-0 left-0 -translate-y-1/2 -translate-x-1/2',
      'bottom-right': 'bottom-0 right-0 translate-y-1/2 translate-x-1/2',
      'bottom-left': 'bottom-0 left-0 translate-y-1/2 -translate-x-1/2'
    };

    if (count === 0) {
      return (
        <div ref={ref} className={cn("relative", className)} {...props}>
          {children}
        </div>
      );
    }

    return (
      <div ref={ref} className={cn("relative", className)} {...props}>
        {children}
        <div
          className={cn(
            "absolute flex items-center justify-center",
            positionClasses[position],
            dot
              ? "w-2 h-2 bg-red-500 rounded-full"
              : "min-w-[18px] h-[18px] bg-red-500 text-white text-xs font-bold rounded-full px-1"
          )}
        >
          {!dot && (count > max ? `${max}+` : count)}
        </div>
      </div>
    );
  }
);

NotificationBadge.displayName = "NotificationBadge";

export { Badge, StatusBadge, NotificationBadge, badgeVariants };