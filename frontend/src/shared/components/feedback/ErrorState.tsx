/**
 * ErrorState - Error display component
 * Used for showing error messages in a consistent way
 */
import { AlertCircle, RefreshCw } from 'lucide-react';
import { cn } from '@/shared/lib/utils';
import { Button } from '@/shared/components/ui/Button';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
  fullScreen?: boolean;
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'An error occurred while loading. Please try again.',
  onRetry,
  className,
  fullScreen = false,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-4 p-8 text-center',
        fullScreen && 'fixed inset-0 bg-background z-50',
        className
      )}
      role="alert"
    >
      <div className="rounded-full bg-destructive/10 p-3">
        <AlertCircle className="h-8 w-8 text-destructive" />
      </div>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground max-w-md">{message}</p>
      </div>
      {onRetry && (
        <Button variant="outline" onClick={onRetry}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Try Again
        </Button>
      )}
    </div>
  );
}
