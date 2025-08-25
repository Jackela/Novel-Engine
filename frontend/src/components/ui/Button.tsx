/**
 * Magic Enhanced Button Component
 * ==============================
 * 
 * Modern button component with Magic UI patterns:
 * - Advanced variant system
 * - Built-in animations and states
 * - Accessibility features
 * - Performance optimizations
 */

import React, { forwardRef, ButtonHTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '../../lib/utils';

const buttonVariants = cva(
  // Base styles
  "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        default: 
          "bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80 transform hover:scale-[1.02] active:scale-[0.98]",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 active:bg-destructive/80 transform hover:scale-[1.02] active:scale-[0.98]",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground active:bg-accent/80 transform hover:scale-[1.02] active:scale-[0.98]",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80 active:bg-secondary/70 transform hover:scale-[1.02] active:scale-[0.98]",
        ghost: 
          "hover:bg-accent hover:text-accent-foreground active:bg-accent/80 transform hover:scale-[1.02] active:scale-[0.98]",
        link: 
          "text-primary underline-offset-4 hover:underline active:text-primary/80",
        gradient:
          "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground hover:from-primary/90 hover:to-primary/70 active:from-primary/80 active:to-primary/60 transform hover:scale-[1.02] active:scale-[0.98] shadow-lg hover:shadow-xl",
        glass:
          "bg-background/80 backdrop-blur-sm border border-border/50 hover:bg-background/90 hover:border-border active:bg-background/70 transform hover:scale-[1.02] active:scale-[0.98]",
        minimal:
          "text-foreground hover:text-primary active:text-primary/80 transition-colors",
        floating:
          "bg-primary text-primary-foreground shadow-lg hover:shadow-xl transform hover:scale-105 hover:-translate-y-0.5 active:scale-95 active:translate-y-0 rounded-full"
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        xl: "h-12 rounded-md px-10 text-base",
        icon: "h-10 w-10",
        "icon-sm": "h-8 w-8",
        "icon-lg": "h-12 w-12"
      },
      loading: {
        true: "cursor-not-allowed opacity-70",
        false: ""
      },
      pulse: {
        true: "animate-pulse",
        false: ""
      },
      glow: {
        true: "shadow-[0_0_20px_rgba(59,130,246,0.5)] hover:shadow-[0_0_30px_rgba(59,130,246,0.7)]",
        false: ""
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      loading: false,
      pulse: false,
      glow: false
    },
  }
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  loadingText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  pulse?: boolean;
  glow?: boolean;
  tooltip?: string;
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      loadingText,
      leftIcon,
      rightIcon,
      pulse,
      glow,
      disabled,
      children,
      tooltip,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    
    const isDisabled = disabled || loading;

    return (
      <Comp
        className={cn(buttonVariants({ 
          variant, 
          size, 
          loading, 
          pulse, 
          glow, 
          className 
        }))}
        ref={ref}
        disabled={isDisabled}
        title={tooltip}
        aria-busy={loading}
        {...props}
      >
        {loading && (
          <svg
            className="mr-2 h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="m4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        
        {!loading && leftIcon && (
          <span className="mr-2 flex items-center">
            {leftIcon}
          </span>
        )}

        <span className="flex-1">
          {loading ? (loadingText || children) : children}
        </span>

        {!loading && rightIcon && (
          <span className="ml-2 flex items-center">
            {rightIcon}
          </span>
        )}
      </Comp>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };