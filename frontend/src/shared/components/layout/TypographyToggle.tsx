/**
 * TypographyToggle - Toggle between default and literary typography modes
 *
 * Why: Editor Canvas needs distinct typography for literary content.
 * The toggle sets data-typography="literary" on html element,
 * which triggers font-serif and literary-specific styles in editor.css.
 */
import { useEffect, useState } from 'react';
import { Type, BookOpen } from 'lucide-react';
import { Button } from '@/shared/components/ui/Button';
import { cn } from '@/lib/utils';

const TYPOGRAPHY_STORAGE_KEY = 'typography-mode';

type TypographyMode = 'default' | 'literary';

function getInitialMode(): TypographyMode {
  if (typeof window === 'undefined') return 'default';

  const stored = localStorage.getItem(TYPOGRAPHY_STORAGE_KEY);
  if (stored === 'literary' || stored === 'default') {
    return stored;
  }

  return 'default';
}

function applyTypographyMode(mode: TypographyMode): void {
  const root = document.documentElement;
  if (mode === 'literary') {
    root.setAttribute('data-typography', 'literary');
  } else {
    root.removeAttribute('data-typography');
  }
}

export function TypographyToggle({ className }: { className?: string }) {
  const [mode, setMode] = useState<TypographyMode>(getInitialMode);

  // Apply mode on mount and when mode changes
  useEffect(() => {
    applyTypographyMode(mode);
    localStorage.setItem(TYPOGRAPHY_STORAGE_KEY, mode);
  }, [mode]);

  const toggleMode = () => {
    setMode((current) => (current === 'default' ? 'literary' : 'default'));
  };

  const isLiterary = mode === 'literary';

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleMode}
      className={cn(className)}
      aria-label={
        isLiterary ? 'Switch to default typography' : 'Switch to literary typography'
      }
      aria-pressed={isLiterary}
    >
      {isLiterary ? <BookOpen className="h-5 w-5" /> : <Type className="h-5 w-5" />}
    </Button>
  );
}
