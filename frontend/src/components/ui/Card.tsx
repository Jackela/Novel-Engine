/**
 * Magic Enhanced Card Component
 * ============================
 * 
 * Flexible card component with Magic UI patterns:
 * - Multiple variants and styles
 * - Built-in animations and hover effects
 * - Accessibility features
 * - Composition-based architecture
 */

import React, { forwardRef } from 'react';
import type { HTMLAttributes } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const cardVariants = cva(
  "rounded-lg border bg-card text-card-foreground transition-all duration-200",
  {
    variants: {
      variant: {
        default: "border-border shadow-sm",
        elevated: "border-border shadow-md hover:shadow-lg",
        outlined: "border-2 border-border bg-transparent",
        ghost: "border-transparent bg-transparent",
        glass: "border-border/50 bg-card/80 backdrop-blur-sm",
        gradient: "border-0 bg-gradient-to-br from-card via-card/90 to-card/80 shadow-lg",
        interactive: "border-border shadow-sm hover:shadow-md hover:border-ring cursor-pointer transform hover:scale-[1.02] active:scale-[0.98]",
        floating: "border-border shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300"
      },
      size: {
        sm: "p-3",
        default: "p-4",
        lg: "p-6",
        xl: "p-8"
      },
      glow: {
        true: "shadow-[0_0_20px_rgba(59,130,246,0.1)] hover:shadow-[0_0_30px_rgba(59,130,246,0.2)]",
        false: ""
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default",
      glow: false
    }
  }
);

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  glow?: boolean;
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, size, glow, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, size, glow, className }))}
      {...props}
    />
  )
);
Card.displayName = "Card";

const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex flex-col space-y-1.5 pb-3", className)}
      {...props}
    />
  )
);
CardHeader.displayName = "CardHeader";

const CardTitle = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn("text-lg font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  )
);
CardTitle.displayName = "CardTitle";

const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p
      ref={ref}
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
);
CardDescription.displayName = "CardDescription";

const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("pt-0", className)}
      {...props}
    />
  )
);
CardContent.displayName = "CardContent";

const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn("flex items-center pt-3", className)}
      {...props}
    />
  )
);
CardFooter.displayName = "CardFooter";

// Advanced Card Components

interface StatCardProps extends CardProps {
  title: string;
  value: string | number;
  description?: string;
  icon?: React.ReactNode;
  trend?: {
    value: number;
    label?: string;
  };
  color?: 'default' | 'success' | 'warning' | 'error' | 'info';
}

const StatCard = forwardRef<HTMLDivElement, StatCardProps>(
  ({ title, value, description, icon, trend, color = 'default', className, ...props }, ref) => {
    const colorClasses = {
      default: 'text-foreground',
      success: 'text-green-600 dark:text-green-400',
      warning: 'text-yellow-600 dark:text-yellow-400',
      error: 'text-red-600 dark:text-red-400',
      info: 'text-blue-600 dark:text-blue-400'
    };

    const trendClasses = {
      positive: 'text-green-600 dark:text-green-400',
      negative: 'text-red-600 dark:text-red-400',
      neutral: 'text-muted-foreground'
    };

    const getTrendColor = (trendValue: number) => {
      if (trendValue > 0) return trendClasses.positive;
      if (trendValue < 0) return trendClasses.negative;
      return trendClasses.neutral;
    };

    const getTrendIcon = (trendValue: number) => {
      if (trendValue > 0) return '↗';
      if (trendValue < 0) return '↘';
      return '→';
    };

    return (
      <Card ref={ref} variant="elevated" className={cn("p-6", className)} {...props}>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <div className="flex items-baseline mt-2">
              <p className={cn("text-2xl font-bold", colorClasses[color])}>{value}</p>
              {trend && (
                <div className={cn("ml-2 flex items-center text-xs", getTrendColor(trend.value))}>
                  <span>{getTrendIcon(trend.value)}</span>
                  <span className="ml-1">{Math.abs(trend.value)}%</span>
                  {trend.label && <span className="ml-1">{trend.label}</span>}
                </div>
              )}
            </div>
            {description && (
              <p className="text-xs text-muted-foreground mt-1">{description}</p>
            )}
          </div>
          {icon && (
            <div className={cn("flex-shrink-0 p-2 rounded-lg", colorClasses[color])}>
              {icon}
            </div>
          )}
        </div>
      </Card>
    );
  }
);
StatCard.displayName = "StatCard";

interface ProgressCardProps extends CardProps {
  title: string;
  progress: number;
  total?: number;
  description?: string;
  color?: 'default' | 'success' | 'warning' | 'error' | 'info';
}

const ProgressCard = forwardRef<HTMLDivElement, ProgressCardProps>(
  ({ title, progress, total, description, color = 'default', className, ...props }, ref) => {
    const percentage = total ? Math.round((progress / total) * 100) : Math.round(progress);
    
    const colorClasses = {
      default: 'bg-primary',
      success: 'bg-green-500',
      warning: 'bg-yellow-500',
      error: 'bg-red-500',
      info: 'bg-blue-500'
    };

    return (
      <Card ref={ref} variant="elevated" className={cn("p-6", className)} {...props}>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">{title}</h3>
            <span className="text-sm font-medium">{percentage}%</span>
          </div>
          
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className={cn("h-2 rounded-full transition-all duration-500", colorClasses[color])}
              style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
          
          {total && (
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{progress.toLocaleString()}</span>
              <span>{total.toLocaleString()}</span>
            </div>
          )}
          
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      </Card>
    );
  }
);
ProgressCard.displayName = "ProgressCard";

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
  StatCard,
  ProgressCard,
  cardVariants
};
