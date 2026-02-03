/**
 * NarrativePage - Story narrative management with full editing capabilities.
 *
 * Why: Provides a full-page writing interface following the professional writing
 * application pattern (sidebar 20%, editor 80%) as specified in NAR-008.
 * Uses the NarrativeEditorLayout component for the split-pane layout.
 */
import { Suspense } from 'react';
import { LoadingSpinner } from '@/shared/components/feedback';
import { NarrativeEditorLayout } from '@/components/narrative/NarrativeEditorLayout';

/**
 * NarrativePage - The main narrative writing page.
 *
 * Why: Serves as the entry point for the narrative editing experience,
 * wrapping the NarrativeEditorLayout in proper page-level concerns
 * (suspense boundaries, error handling, page chrome).
 */
export default function NarrativePage() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Loading narrative..." />}>
      <div className="flex h-full flex-col" data-testid="narrative-page">
        {/* Page header */}
        <header className="shrink-0 border-b border-border bg-background px-6 py-4">
          <h1 className="text-2xl font-bold tracking-tight">Narrative Studio</h1>
          <p className="text-sm text-muted-foreground">
            Create and manage your story narrative
          </p>
        </header>

        {/* Main content: NarrativeEditorLayout (sidebar 20% + editor 80%) */}
        <div className="flex-1 overflow-hidden">
          <NarrativeEditorLayout />
        </div>
      </div>
    </Suspense>
  );
}
