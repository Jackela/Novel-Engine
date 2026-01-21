/**
 * LoadingSpinner - Loading indicator component
 * Used for suspense boundaries and async operations
 */
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  fullScreen?: boolean;
  text?: string;
  className?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-8 w-8',
  lg: 'h-12 w-12',
} as const;

export function LoadingSpinner({
  size = 'md',
  fullScreen = false,
  text,
  className,
}: LoadingSpinnerProps) {
  const spinner = (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3',
        fullScreen && 'fixed inset-0 bg-background z-50',
        className
      )}
      role="status"
      aria-label={text || 'Loading'}
    >
      <Loader2
        className={cn(
          sizeClasses[size],
          'animate-spin text-muted-foreground'
        )}
      />
      {text && (
        <p className="text-sm text-muted-foreground">{text}</p>
      )}
      <span className="sr-only">{text || 'Loading...'}</span>
    </div>
  );

  return spinner;
}
