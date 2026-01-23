/**
 * VisuallyHidden - Hides content visually but keeps it accessible
 */
import type { ReactNode, ElementType } from 'react';
import { cn } from '@/lib/utils';

interface VisuallyHiddenProps {
  children: ReactNode;
  as?: ElementType;
  className?: string;
}

export function VisuallyHidden({
  children,
  as: Component = 'span',
  className,
}: VisuallyHiddenProps) {
  return (
    <Component
      className={cn(
        'absolute -m-px h-px w-px overflow-hidden whitespace-nowrap border-0 p-0',
        '[clip:rect(0,0,0,0)]',
        className
      )}
    >
      {children}
    </Component>
  );
}
