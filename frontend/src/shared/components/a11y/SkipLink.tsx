/**
 * SkipLink - Accessibility skip navigation link
 * Allows keyboard users to skip to main content
 */
import { cn } from '@/lib/utils';

interface SkipLinkProps {
  targetId: string;
  text?: string;
  className?: string;
}

export function SkipLink({
  targetId,
  text = 'Skip to main content',
  className,
}: SkipLinkProps) {
  return (
    <a
      href={`#${targetId}`}
      className={cn(
        'sr-only focus:not-sr-only',
        'focus:fixed focus:top-4 focus:left-4 focus:z-[9999]',
        'focus:px-4 focus:py-2',
        'focus:bg-primary focus:text-primary-foreground',
        'focus:rounded-md focus:outline-none focus:ring-2 focus:ring-ring',
        'transition-all',
        className
      )}
    >
      {text}
    </a>
  );
}
