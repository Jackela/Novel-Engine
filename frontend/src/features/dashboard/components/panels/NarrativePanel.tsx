/**
 * NarrativePanel - Current narrative output
 * Shows the latest generated narrative content
 */
import { BookOpen, Sparkles } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/shared/components/ui/Card';

export default function NarrativePanel() {
  return (
    <Card className="h-full" data-testid="narrative-panel">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          Narrative Output
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Generation indicator */}
          <div className="flex items-center gap-2 rounded-lg bg-primary/10 p-2">
            <Sparkles className="h-4 w-4 animate-pulse text-primary" />
            <span className="text-sm text-primary">Generating narrative...</span>
          </div>

          {/* Latest narrative */}
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="leading-relaxed text-muted-foreground">
              The morning mist clung to the cobblestone streets as Aldric made his way
              through the quiet marketplace. Merchants were just beginning to set up
              their stalls, their hushed voices carrying in the cool air.
            </p>
            <p className="mt-3 leading-relaxed text-muted-foreground">
              He paused at the fountain in the center square, eyes scanning the crowd
              for any sign of his contact. The message had been clear: dawn at the
              market, come alone.
            </p>
          </div>

          {/* Word count */}
          <div className="flex items-center justify-between border-t border-border pt-2 text-xs text-muted-foreground">
            <span>Last updated: 2 min ago</span>
            <span>1,247 words generated</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
