/**
 * BeatSuggestionDialog - AI-powered beat suggestion UI.
 *
 * Why: Writer's block breaker - displays 3 AI-suggested beats in a dialog.
 * Each suggestion shows beat type badge, content preview, and rationale.
 * Clicking inserts the suggestion into the beat list.
 */

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sparkles, Loader2, Lightbulb, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSuggestBeats } from '../api/beatSuggestionApi';
import type { BeatResponse, BeatType } from '@/types/schemas';

/**
 * Beat type configuration for visual styling and labels.
 */
const BEAT_TYPE_CONFIG: Record<
  BeatType,
  { label: string; borderColor: string; bgColor: string }
> = {
  action: {
    label: 'Action',
    borderColor: 'border-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950',
  },
  dialogue: {
    label: 'Dialogue',
    borderColor: 'border-emerald-500',
    bgColor: 'bg-emerald-50 dark:bg-emerald-950',
  },
  reaction: {
    label: 'Reaction',
    borderColor: 'border-amber-500',
    bgColor: 'bg-amber-50 dark:bg-amber-950',
  },
  revelation: {
    label: 'Revelation',
    borderColor: 'border-purple-500',
    bgColor: 'bg-purple-50 dark:bg-purple-950',
  },
  transition: {
    label: 'Transition',
    borderColor: 'border-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-950',
  },
  description: {
    label: 'Description',
    borderColor: 'border-cyan-500',
    bgColor: 'bg-cyan-50 dark:bg-cyan-950',
  },
};

interface BeatSuggestionDialogProps {
  /** Scene ID to generate suggestions for */
  sceneId: string;
  /** Current beats in the scene */
  currentBeats: BeatResponse[];
  /** Scene context description */
  sceneContext: string;
  /** Optional mood target for suggestions */
  moodTarget?: number | undefined;
  /** Callback when a suggestion is selected */
  onSelectSuggestion: (suggestion: {
    content: string;
    beat_type: BeatType;
    mood_shift: number;
  }) => void;
  /** Optional CSS class name */
  className?: string;
}

/**
 * BeatSuggestionDialog - Dialog with AI-generated beat suggestions.
 */
export function BeatSuggestionDialog({
  sceneId,
  currentBeats,
  sceneContext,
  moodTarget,
  onSelectSuggestion,
  className,
}: BeatSuggestionDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const suggestBeats = useSuggestBeats();

  // Prepare current beats for API
  const currentBeatsForApi = currentBeats.map((beat) => ({
    beat_type: beat.beat_type,
    content: beat.content,
    mood_shift: beat.mood_shift,
  }));

  // Generate suggestions when dialog opens
  useEffect(() => {
    if (isOpen && !suggestBeats.data) {
      suggestBeats.mutate({
        sceneId,
        currentBeats: currentBeatsForApi,
        sceneContext,
        moodTarget,
      });
    }
  }, [isOpen, sceneId, currentBeatsForApi, sceneContext, moodTarget, suggestBeats]);

  // Handle suggestion selection
  const handleSelectSuggestion = (
    beatType: string,
    content: string,
    moodShift: number
  ) => {
    onSelectSuggestion({
      content,
      beat_type: beatType as BeatType,
      mood_shift: moodShift,
    });
    setIsOpen(false);
    suggestBeats.reset();
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className={cn('gap-1.5', className)}
          disabled={suggestBeats.isPending}
        >
          {suggestBeats.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5 text-purple-500" />
          )}
          Spark
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-amber-500" />
            <DialogTitle className="text-lg">AI Beat Suggestions</DialogTitle>
          </div>
          <DialogDescription>
            Click a suggestion to insert it into your beat list
          </DialogDescription>
        </DialogHeader>

        {/* Loading State */}
        {suggestBeats.isPending && (
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
              <p className="mt-3 text-sm text-muted-foreground">
                Generating suggestions...
              </p>
            </div>
          </div>
        )}

        {/* Error State */}
        {suggestBeats.error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
            <p className="text-sm text-destructive">
              Failed to generate suggestions. Please try again.
            </p>
          </div>
        )}

        {/* Suggestions */}
        {suggestBeats.data && !suggestBeats.isPending && (
          <ScrollArea className="h-72 pr-4">
            <div className="space-y-3">
              {suggestBeats.data.suggestions.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  <Zap className="mx-auto h-10 w-10 opacity-50" />
                  <p className="mt-3 text-sm">No suggestions available</p>
                </div>
              ) : (
                suggestBeats.data.suggestions.map((suggestion, index) => {
                  const typeConfig = BEAT_TYPE_CONFIG[
                    suggestion.beat_type as BeatType
                  ] || {
                    label: suggestion.beat_type,
                    borderColor: 'border-gray-500',
                    bgColor: 'bg-gray-50 dark:bg-gray-950',
                  };

                  return (
                    <button
                      key={index}
                      onClick={() =>
                        handleSelectSuggestion(
                          suggestion.beat_type,
                          suggestion.content,
                          suggestion.mood_shift
                        )
                      }
                      className={cn(
                        'w-full rounded-lg border-l-4 p-4 text-left transition-all hover:shadow-md',
                        typeConfig.borderColor,
                        typeConfig.bgColor
                      )}
                    >
                      {/* Type Badge */}
                      <div className="mb-2">
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-xs',
                            typeConfig.borderColor.replace('border-', 'text-')
                          )}
                        >
                          {typeConfig.label}
                        </Badge>
                      </div>

                      {/* Content */}
                      <p className="mb-2 text-sm leading-relaxed">
                        {suggestion.content}
                      </p>

                      {/* Rationale */}
                      {suggestion.rationale && (
                        <p className="text-xs italic text-muted-foreground">
                          "{suggestion.rationale}"
                        </p>
                      )}
                    </button>
                  );
                })
              )}
            </div>
          </ScrollArea>
        )}

        <DialogFooter className="flex-col gap-2 sm:flex-col">
          {/* Regenerate Button */}
          {suggestBeats.data && !suggestBeats.isPending && (
            <Button
              variant="outline"
              className="w-full gap-1.5"
              onClick={() =>
                suggestBeats.mutate({
                  sceneId,
                  currentBeats: currentBeatsForApi,
                  sceneContext,
                  moodTarget,
                })
              }
            >
              <Sparkles className="h-3.5 w-3.5" />
              Generate new suggestions
            </Button>
          )}
          <Button variant="ghost" onClick={() => setIsOpen(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Also export as Popover for backward compatibility
export const BeatSuggestionPopover = BeatSuggestionDialog;

export default BeatSuggestionDialog;
