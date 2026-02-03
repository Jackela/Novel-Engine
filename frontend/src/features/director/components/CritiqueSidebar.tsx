/**
 * CritiqueSidebar - AI-powered scene critique feedback panel.
 *
 * Why: Provides AI-generated feedback on scene writing quality across
 * multiple craft dimensions (pacing, voice, showing, dialogue). Displays
 * feedback as checklist items with severity icons and actionable suggestions.
 */

import { useState, useEffect } from 'react';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
  SheetFooter,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  FileText,
  Loader2,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCritiqueScene } from '../api/critiqueApi';
import type { CritiqueCategoryScore } from '@/types/schemas';

/**
 * Category configuration for visual styling and icons.
 */
const CATEGORY_CONFIG: Record<
  string,
  { label: string; icon: typeof FileText; color: string }
> = {
  pacing: { label: 'Pacing', icon: FileText, color: 'text-blue-500' },
  voice: { label: 'Voice', icon: FileText, color: 'text-purple-500' },
  showing: { label: 'Showing', icon: FileText, color: 'text-amber-500' },
  dialogue: { label: 'Dialogue', icon: FileText, color: 'text-emerald-500' },
};

/**
 * Get severity icon based on score.
 */
function getSeverityIcon(score: number) {
  if (score >= 8) {
    return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
  }
  if (score >= 6) {
    return <AlertTriangle className="h-4 w-4 text-amber-500" />;
  }
  if (score >= 4) {
    return <AlertCircle className="h-4 w-4 text-orange-500" />;
  }
  return <XCircle className="h-4 w-4 text-red-500" />;
}

/**
 * Get severity badge color based on score.
 */
function getSeverityBadge(score: number): string {
  if (score >= 8) {
    return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100';
  }
  if (score >= 6) {
    return 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100';
  }
  if (score >= 4) {
    return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100';
  }
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100';
}

/**
 * CritiqueItem - A single feedback point within a category.
 */
function CritiqueItem({
  text,
  type,
}: {
  text: string;
  type: 'issue' | 'suggestion';
}) {
  const isIssue = type === 'issue';
  return (
    <div className="flex gap-2 py-1">
      <span className={cn('text-sm', isIssue ? 'text-red-500' : 'text-blue-500')}>
        {isIssue ? '•' : '→'}
      </span>
      <span className="text-sm text-muted-foreground">{text}</span>
    </div>
  );
}

/**
 * CategorySection - Feedback grouped by category.
 */
function CategorySection({ category }: { category: CritiqueCategoryScore }) {
  const config = CATEGORY_CONFIG[category.category] || {
    label: category.category,
    icon: FileText,
    color: 'text-gray-500',
  };
  const Icon = config.icon;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className={cn('h-4 w-4', config.color)} />
          <span className="font-medium">{config.label}</span>
        </div>
        <div className="flex items-center gap-2">
          {getSeverityIcon(category.score)}
          <Badge variant="outline" className={cn('text-xs', getSeverityBadge(category.score))}>
            {category.score}/10
          </Badge>
        </div>
      </div>

      {category.issues.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-muted-foreground">Issues:</p>
          {category.issues.map((issue, idx) => (
            <CritiqueItem key={`issue-${idx}`} text={issue} type="issue" />
          ))}
        </div>
      )}

      {category.suggestions.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-muted-foreground">Suggestions:</p>
          {category.suggestions.map((suggestion, idx) => (
            <CritiqueItem key={`suggestion-${idx}`} text={suggestion} type="suggestion" />
          ))}
        </div>
      )}

      <Separator className="my-2" />
    </div>
  );
}

interface CritiqueSidebarProps {
  /** Scene ID to critique */
  sceneId: string;
  /** Scene text content */
  sceneText: string;
  /** Optional writer's goals for the scene */
  sceneGoals?: string[] | undefined;
  /** Optional CSS class name */
  className?: string;
}

/**
 * CritiqueSidebar - AI feedback panel for scene critique.
 */
export function CritiqueSidebar({
  sceneId,
  sceneText,
  sceneGoals,
  className,
}: CritiqueSidebarProps) {
  const [isOpen, setIsOpen] = useState(false);
  const critiqueScene = useCritiqueScene();

  // Generate critique when sidebar opens
  useEffect(() => {
    if (isOpen && !critiqueScene.data && sceneText.length >= 50) {
      critiqueScene.mutate({
        sceneId,
        sceneText,
        sceneGoals,
      });
    }
  }, [isOpen, sceneId, sceneText, sceneGoals, critiqueScene]);

  const handleCritiqueScene = () => {
    critiqueScene.mutate({
      sceneId,
      sceneText,
      sceneGoals,
    });
  };

  const critique = critiqueScene.data;
  const isLoading = critiqueScene.isPending;
  const error = critiqueScene.data?.error || critiqueScene.error;

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('gap-2', className)}
          disabled={sceneText.length < 50}
        >
          <FileText className="h-4 w-4" />
          Critique
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-full sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Scene Critique</SheetTitle>
          <SheetDescription>
            AI-powered feedback on your scene's writing quality
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="h-[calc(100vh-180px)] py-4">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="mt-4 text-sm text-muted-foreground">
                Analyzing scene...
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Critique failed
              </p>
              <p className="mt-1 text-xs text-red-600 dark:text-red-400">
                {typeof error === 'string' ? error : error?.message || 'An error occurred'}
              </p>
            </div>
          )}

          {critique && !isLoading && (
            <div className="space-y-6">
              {/* Overall Score */}
              <div className="rounded-lg border bg-card p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Overall Score</span>
                  <Badge
                    variant="outline"
                    className={cn('text-lg font-bold', getSeverityBadge(critique.overall_score))}
                  >
                    {critique.overall_score}/10
                  </Badge>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{critique.summary}</p>
              </div>

              {/* Highlights */}
              {critique.highlights.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                    What Works Well
                  </h4>
                  <ul className="space-y-1">
                    {critique.highlights.map((highlight, idx) => (
                      <li key={`highlight-${idx}`} className="flex gap-2 text-sm">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        <span className="text-muted-foreground">{highlight}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <Separator />

              {/* Category Scores */}
              <div className="space-y-4">
                <h4 className="text-sm font-semibold">Category Breakdown</h4>
                {critique.category_scores.map((category) => (
                  <CategorySection key={category.category} category={category} />
                ))}
              </div>
            </div>
          )}

          {!critique && !isLoading && !error && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground/50" />
              <p className="mt-4 text-sm text-muted-foreground">
                Click &quot;Critique Scene&quot; to analyze your scene
              </p>
            </div>
          )}
        </ScrollArea>

        <SheetFooter className="gap-2">
          <Button
            variant="outline"
            onClick={handleCritiqueScene}
            disabled={isLoading || sceneText.length < 50}
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Critique Scene'
            )}
          </Button>
          <Button onClick={() => setIsOpen(false)}>Close</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
