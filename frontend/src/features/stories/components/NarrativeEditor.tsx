/**
 * NarrativeEditor - Immersive writing interface
 *
 * Uses shadcn/ui components for a clean, distraction-free
 * writing experience with real-time streaming support.
 */
import { useCallback, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useStoryStream, type WorldContext, type StreamRequest } from '../hooks/useStoryStream';

interface NarrativeEditorProps {
  /** Initial world context for generation */
  worldContext?: WorldContext;
  /** Callback when content changes */
  onContentChange?: (content: string) => void;
  /** Callback when stream completes */
  onComplete?: () => void;
}

/**
 * Default world context for demo/testing.
 * In production, this would come from the Weaver or story state.
 */
const DEFAULT_WORLD_CONTEXT: WorldContext = {
  characters: [
    { id: 'char-1', name: 'Elena', type: 'character', description: 'A young scholar' },
    { id: 'char-2', name: 'Marcus', type: 'character', description: 'A wandering knight' },
  ],
  locations: [
    { id: 'loc-1', name: 'The Ancient Library', type: 'location' },
  ],
  entities: [],
  current_scene: 'The journey begins',
  narrative_style: 'epic fantasy',
};

export function NarrativeEditor({
  worldContext = DEFAULT_WORLD_CONTEXT,
  onContentChange,
  onComplete,
}: NarrativeEditorProps) {
  const {
    content,
    status,
    error,
    metadata,
    startStream,
    cancelStream,
    reset,
  } = useStoryStream();

  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const isGenerating = status === 'connecting' || status === 'streaming';

  // Auto-scroll to bottom when content updates
  useEffect(() => {
    if (scrollAreaRef.current && status === 'streaming') {
      const viewport = scrollAreaRef.current.querySelector('[data-radix-scroll-area-viewport]');
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight;
      }
    }
  }, [content, status]);

  // Notify parent of content changes
  useEffect(() => {
    onContentChange?.(content);
  }, [content, onContentChange]);

  // Notify parent when complete
  useEffect(() => {
    if (status === 'complete') {
      onComplete?.();
    }
  }, [status, onComplete]);

  const handleNewChapter = useCallback(() => {
    const request: StreamRequest = {
      prompt: 'Continue the story with a new chapter. Build upon the existing narrative.',
      world_context: worldContext,
      chapter_title: `Chapter ${Math.floor(Date.now() / 1000) % 100}`,
      tone: 'mysterious',
      max_tokens: 2000,
    };
    startStream(request);
  }, [worldContext, startStream]);

  const handleCancel = useCallback(() => {
    cancelStream();
  }, [cancelStream]);

  const handleReset = useCallback(() => {
    reset();
  }, [reset]);

  return (
    <div className="flex h-full flex-col gap-6">
      {/* Editor Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Story Editor</h2>
          <p className="text-sm text-muted-foreground">
            Generate and edit your narrative
          </p>
        </div>
        <div className="flex gap-2">
          {isGenerating ? (
            <Button
              variant="destructive"
              onClick={handleCancel}
              aria-label="Cancel generation"
            >
              Cancel
            </Button>
          ) : (
            <Button
              onClick={handleNewChapter}
              disabled={isGenerating}
              aria-label="New Chapter"
            >
              New Chapter
            </Button>
          )}
          {content && status !== 'streaming' && (
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={isGenerating}
            >
              Clear
            </Button>
          )}
        </div>
      </div>

      {/* Main Editor Area */}
      <Card className="flex-1">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Narrative</CardTitle>
            {/* Status Indicators */}
            {isGenerating && (
              <div
                className="flex items-center gap-2 text-sm text-muted-foreground"
                data-testid="generating-indicator"
              >
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-primary" />
                Generating...
              </div>
            )}
            {status === 'complete' && metadata && (
              <span className="text-xs text-muted-foreground">
                {metadata.total_characters} chars in {metadata.generation_time_ms}ms
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex-1 p-0">
          <ScrollArea
            ref={scrollAreaRef}
            className="h-[calc(100vh-20rem)] px-6"
            data-testid="narrative-editor"
          >
            {content ? (
              <div className="prose prose-sm dark:prose-invert max-w-none py-4">
                <div
                  className="whitespace-pre-wrap leading-relaxed"
                  dangerouslySetInnerHTML={{
                    __html: content
                      .replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold mt-6 mb-2">$1</h2>')
                      .replace(/^\*(.+)\*$/gm, '<p class="italic text-muted-foreground">$1</p>')
                      .replace(/\n\n/g, '</p><p class="my-2">')
                      .replace(/^/, '<p class="my-2">')
                      .replace(/$/, '</p>'),
                  }}
                />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center py-12 text-muted-foreground">
                {status === 'idle' && (
                  <p>Click &quot;New Chapter&quot; to start generating your story</p>
                )}
                {status === 'connecting' && (
                  <p data-testid="generating-indicator">Connecting...</p>
                )}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Error Display */}
      {status === 'error' && error && (
        <Card className="border-destructive" data-testid="generation-error">
          <CardContent className="py-4">
            <p className="text-sm text-destructive">
              Error: {error}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={handleNewChapter}
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Manual Edit Area (optional) */}
      {status === 'complete' && content && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-sm">Continue Writing</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <Textarea
              placeholder="Add your own text to continue the story..."
              className="min-h-[100px] resize-none"
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
