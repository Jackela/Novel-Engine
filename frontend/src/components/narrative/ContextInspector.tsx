/**
 * Context Inspector - BRAIN-036-02
 * BRAIN-036-04: Manual Chunk Selection
 * BRAIN-036-05: Context Window Display
 *
 * Sliding panel component for viewing AI RAG context.
 * Shows retrieved chunks with source info, relevance scores, and token counts.
 * Allows manual selection of chunks for regeneration.
 * Displays context window usage with progress bar.
 */

import { useEffect, useState } from 'react';
import { Brain, CheckCircle2, FileText, Hash, Loader2, RefreshCw, X, AlertTriangle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Progress } from '@/components/ui/progress';
import { brainSettingsApi, type RetrievedChunkResponse, type RAGContextResponse } from '@/features/routing/api/brainSettingsApi';
import { toast } from 'sonner';

interface ContextInspectorProps {
  /** Whether the panel is open */
  open: boolean;
  /** Called when panel should close */
  onClose: () => void;
  /** Query to retrieve context for (e.g., scene content) */
  query: string;
  /** Optional scene ID for context */
  sceneId?: string;
  /** Optional callback for regenerate with selected chunks */
  onRegenerateWithChunks?: (chunkIds: string[]) => void;
  /** Optional context token limit (defaults to 4000) */
  contextTokenLimit?: number;
}

/**
 * Source type badge color mapping
 */
const SOURCE_TYPE_COLORS: Record<string, string> = {
  CHARACTER: 'bg-purple-100 text-purple-800 hover:bg-purple-200',
  LORE: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
  SCENE: 'bg-green-100 text-green-800 hover:bg-green-200',
  PLOTLINE: 'bg-orange-100 text-orange-800 hover:bg-orange-200',
  ITEM: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  LOCATION: 'bg-teal-100 text-teal-800 hover:bg-teal-200',
};

/**
 * Context Inspector Panel Component
 *
 * Displays retrieved RAG chunks with:
 * - Source information (type, ID)
 * - Relevance score
 * - Token count
 * - Chunk content
 * - BRAIN-036-05: Context window usage display
 */
export function ContextInspector({ open, onClose, query, sceneId, onRegenerateWithChunks, contextTokenLimit = 4000 }: ContextInspectorProps) {
  const [context, setContext] = useState<RAGContextResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // BRAIN-036-04: Track selected chunks for manual regeneration
  const [selectedChunkIds, setSelectedChunkIds] = useState<Set<string>>(new Set());

  // Fetch context when query changes or panel opens
  useEffect(() => {
    if (!open || !query) return;

    const fetchContext = async () => {
      setIsLoading(true);
      setError(null);
      // BRAIN-036-04: Clear selections when fetching new context
      setSelectedChunkIds(new Set());
      try {
        const result = await brainSettingsApi.getRAGContext(query, sceneId, 10);
        setContext(result);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load context';
        setError(message);
        console.error('ContextInspector: fetch error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchContext();
  }, [open, query, sceneId]);

  // BRAIN-036-04: Handle chunk selection
  const toggleChunkSelection = (chunkId: string) => {
    setSelectedChunkIds((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  };

  // BRAIN-036-04: Select all chunks
  const selectAllChunks = () => {
    if (context) {
      setSelectedChunkIds(new Set(context.chunks.map((c) => c.chunk_id)));
    }
  };

  // BRAIN-036-04: Deselect all chunks
  const deselectAllChunks = () => {
    setSelectedChunkIds(new Set());
  };

  // BRAIN-036-04: Handle regenerate with selected chunks
  const handleRegenerate = () => {
    if (selectedChunkIds.size === 0) {
      toast.error('Please select at least one chunk to regenerate with');
      return;
    }

    const selectedIds = Array.from(selectedChunkIds);

    // Call the parent callback if provided
    if (onRegenerateWithChunks) {
      onRegenerateWithChunks(selectedIds);
      toast.success(`Regenerating with ${selectedIds.length} selected chunk${selectedIds.length > 1 ? 's' : ''}`);
    } else {
      // For now, just log the selected chunks
      console.log('BRAIN-036-04: Selected chunks for regeneration:', selectedIds);
      toast.info(`Selected ${selectedIds.length} chunk${selectedIds.length > 1 ? 's' : ''} for regeneration. Connect to scene generation to complete.`);
    }
  };

  // BRAIN-036-05: Calculate context window usage
  const getContextWindowStatus = () => {
    if (!context) return null;

    const usedTokens = context.total_tokens;
    const limit = contextTokenLimit;
    const percentage = Math.min((usedTokens / limit) * 100, 100);
    const isNearLimit = percentage >= 80;
    const isAtLimit = percentage >= 95;

    return { usedTokens, limit, percentage, isNearLimit, isAtLimit };
  };

  const contextWindowStatus = getContextWindowStatus();

  return (
    <Sheet open={open} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="w-full sm:max-w-lg flex flex-col gap-0 p-0">
        {/* Header */}
        <SheetHeader className="border-b px-6 py-4 space-y-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="h-5 w-5 text-primary" />
              <SheetTitle>AI Context Inspector</SheetTitle>
            </div>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
              <X className="h-4 w-4" />
              <span className="sr-only">Close</span>
            </Button>
          </div>
          <SheetDescription className="text-left">
            {context ? (
              <>
                {context.chunk_count} chunks retrieved · {context.total_tokens} tokens
                {selectedChunkIds.size > 0 && (
                  <span className="ml-2 text-primary font-medium">
                    ({selectedChunkIds.size} selected)
                  </span>
                )}
              </>
            ) : (
              'Retrieving context for current scene...'
            )}
          </SheetDescription>
          {/* BRAIN-036-04: Selection actions */}
          {context && context.chunks.length > 0 && (
            <div className="flex items-center gap-2 pt-2">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={selectAllChunks}
                disabled={selectedChunkIds.size === context.chunks.length}
              >
                Select All
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={deselectAllChunks}
                disabled={selectedChunkIds.size === 0}
              >
                Deselect All
              </Button>
            </div>
          )}
        </SheetHeader>

        {/* BRAIN-036-05: Context Window Display */}
        {contextWindowStatus && (
          <div className="border-b px-6 py-3 bg-muted/30">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Context Window</span>
                <div className="flex items-center gap-2">
                  <span className="font-medium">
                    {contextWindowStatus.usedTokens.toLocaleString()} / {contextWindowStatus.limit.toLocaleString()} tokens
                  </span>
                  <span className={`text-xs font-medium ${
                    contextWindowStatus.isAtLimit
                      ? 'text-destructive'
                      : contextWindowStatus.isNearLimit
                        ? 'text-orange-600 dark:text-orange-400'
                        : 'text-muted-foreground'
                  }`}>
                    ({contextWindowStatus.percentage.toFixed(0)}%)
                  </span>
                </div>
              </div>
              <Progress
                value={contextWindowStatus.percentage}
                className={contextWindowStatus.isAtLimit ? '[&>div]:bg-destructive' : contextWindowStatus.isNearLimit ? '[&>div]:bg-orange-500' : ''}
              />
              {/* BRAIN-036-05: Warning when approaching limit */}
              {contextWindowStatus.isNearLimit && (
                <div className={`flex items-center gap-2 text-xs ${
                  contextWindowStatus.isAtLimit
                    ? 'text-destructive'
                    : 'text-orange-600 dark:text-orange-400'
                }`}>
                  <AlertTriangle className="h-3 w-3" />
                  <span>
                    {contextWindowStatus.isAtLimit
                      ? 'Context window nearly full. Consider reducing chunk count or size.'
                      : 'Approaching context window limit.'}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <ScrollArea className="h-full px-6 py-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">Searching knowledge base...</p>
                </div>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="rounded-full bg-destructive/10 p-3 mb-3">
                  <FileText className="h-6 w-6 text-destructive" />
                </div>
                <p className="text-sm font-medium">Failed to load context</p>
                <p className="text-xs text-muted-foreground mt-1">{error}</p>
              </div>
            ) : context && context.chunks.length > 0 ? (
              <div className="space-y-4">
                {context.chunks.map((chunk, index) => (
                  <ChunkCard
                    key={chunk.chunk_id}
                    chunk={chunk}
                    index={index}
                    selected={selectedChunkIds.has(chunk.chunk_id)}
                    onToggleSelection={() => toggleChunkSelection(chunk.chunk_id)}
                  />
                ))}
              </div>
            ) : context ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="rounded-full bg-muted p-3 mb-3">
                  <FileText className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="text-sm font-medium">No context found</p>
                <p className="text-xs text-muted-foreground mt-1">
                  The knowledge base has no relevant information for this query.
                </p>
              </div>
            ) : null}
          </ScrollArea>
        </div>

        {/* Footer with sources and BRAIN-036-04: Regenerate action */}
        {context && (
          <div className="border-t px-6 py-3 bg-muted/30 space-y-3">
            {/* BRAIN-036-04: Regenerate button */}
            {selectedChunkIds.size > 0 && (
              <Button
                onClick={handleRegenerate}
                className="w-full"
                size="sm"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Regenerate with {selectedChunkIds.size} Selected Chunk{selectedChunkIds.size > 1 ? 's' : ''}
              </Button>
            )}
            {/* Sources */}
            {context.sources.length > 0 && (
              <>
                <p className="text-xs text-muted-foreground mb-2">Sources:</p>
                <div className="flex flex-wrap gap-1">
                  {context.sources.map((source) => (
                    <Badge key={source} variant="outline" className="text-xs">
                      {source}
                    </Badge>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

/**
 * Individual chunk card component
 * BRAIN-036-03: Visual distinction for used vs unused chunks
 * BRAIN-036-04: Manual chunk selection with checkbox
 */
interface ChunkCardProps {
  chunk: RetrievedChunkResponse;
  index: number;
  /** Whether this chunk is selected */
  selected: boolean;
  /** Called when checkbox is toggled */
  onToggleSelection: () => void;
}

function ChunkCard({ chunk, index, selected, onToggleSelection }: ChunkCardProps) {
  const scoreColor = chunk.score >= 0.8 ? 'text-green-600' : chunk.score >= 0.6 ? 'text-yellow-600' : 'text-orange-600';

  // BRAIN-036-03: Visual styling for used chunks
  const usedBgClass = chunk.used ? 'bg-green-50/50 border-green-200 dark:bg-green-950/30 dark:border-green-800' : 'border-border';
  // BRAIN-036-04: Additional styling for selected chunks
  const selectedBgClass = selected ? 'ring-2 ring-primary ring-offset-2' : '';
  const combinedBgClass = `${usedBgClass} ${selectedBgClass}`.trim();

  const usedBadge = chunk.used ? (
    <div className="flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400" title="This chunk was used in the response">
      <CheckCircle2 className="h-3 w-3" />
      <span>Used</span>
    </div>
  ) : null;

  return (
    <div className={`border rounded-lg p-4 space-y-3 hover:bg-muted/50 transition-colors ${combinedBgClass}`}>
      {/* Header with checkbox, source, and score */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* BRAIN-036-04: Checkbox for manual selection */}
          <Checkbox
            checked={selected}
            onCheckedChange={onToggleSelection}
            className="cursor-pointer"
            aria-label={`Select chunk ${index + 1}`}
          />
          <span className="text-xs font-mono text-muted-foreground">#{index + 1}</span>
          <Badge
            className={SOURCE_TYPE_COLORS[chunk.source_type] || 'bg-gray-100 text-gray-800'}
          >
            {chunk.source_type}
          </Badge>
          <span className="text-sm font-medium">{chunk.source_id}</span>
          {usedBadge}
        </div>
        <div className="flex items-center gap-1" title={`Relevance: ${(chunk.score * 100).toFixed(0)}%`}>
          <Hash className="h-3 w-3 text-muted-foreground" />
          <span className={`text-sm font-semibold ${scoreColor}`}>
            {chunk.score.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Chunk content */}
      <div className="text-sm leading-relaxed whitespace-pre-wrap">
        {chunk.content}
      </div>

      {/* Metadata footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t">
        <span>{chunk.token_count} tokens</span>
        <span className="font-mono">{chunk.chunk_id.slice(0, 8)}...</span>
      </div>
    </div>
  );
}

export default ContextInspector;
