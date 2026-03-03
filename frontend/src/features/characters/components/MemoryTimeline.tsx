/**
 * MemoryTimeline Component
 *
 * Displays character memories in a vertical timeline format.
 *
 * Features:
 * - Sorted by timestamp (newest first)
 * - Core memory highlighting with star icon
 * - Importance level badges
 * - Tag display
 * - Virtualized list using react-window for performance with 50+ memories
 */
import React, { useMemo, useRef, useCallback } from 'react';
import { VariableSizeList as List } from 'react-window';
import { Brain, Star, Calendar, Tag } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { CharacterMemory } from '@/types/schemas';

type Props = {
  memories: CharacterMemory[] | undefined;
};

const LIST_HEIGHT = 320;
const ITEM_PADDING = 12; // space-y-3 = 12px gap between items

const IMPORTANCE_COLORS: Record<string, string> = {
  minor: 'bg-zinc-500/20 text-zinc-700 dark:text-zinc-300',
  moderate: 'bg-blue-500/20 text-blue-700 dark:text-blue-300',
  significant: 'bg-purple-500/20 text-purple-700 dark:text-purple-300',
  core: 'bg-amber-500/20 text-amber-700 dark:text-amber-300',
};

function formatDate(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Estimate memory card height based on content.
 * Used for initial virtual list sizing.
 */
function estimateMemoryHeight(memory: CharacterMemory): number {
  const baseHeight = 80; // Header + footer + padding
  const contentLines = Math.ceil(memory.content.length / 60); // ~60 chars per line
  const tagsHeight = memory.tags.length > 0 ? 28 : 0;
  return baseHeight + Math.min(contentLines * 20, 120) + tagsHeight;
}

type MemoryCardProps = {
  memory: CharacterMemory;
};

const MemoryCard = React.memo(function MemoryCard({ memory }: MemoryCardProps) {
  const isCoreMemory = memory.is_core_memory;

  return (
    <div
      className={`relative rounded-lg border p-4 transition-colors ${
        isCoreMemory ? 'border-amber-500/50 bg-amber-500/5' : 'border-border bg-card'
      }`}
      style={{ marginBottom: ITEM_PADDING }}
    >
      {isCoreMemory && (
        <div className="absolute -right-2 -top-2">
          <Star className="h-5 w-5 fill-amber-500 text-amber-500" />
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span>{formatDate(memory.timestamp)}</span>
          </div>
          <Badge
            variant="outline"
            className={IMPORTANCE_COLORS[memory.importance_level]}
          >
            {memory.importance_level}
          </Badge>
        </div>

        <p className="text-sm leading-relaxed">{memory.content}</p>

        {memory.tags.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <Tag className="h-3 w-3 text-muted-foreground" />
            {memory.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Brain className="h-3 w-3" />
          <span>Importance: {memory.importance}/10</span>
        </div>
      </div>
    </div>
  );
});

/**
 * Virtualized row component for react-window.
 */
interface MemoryRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    memories: CharacterMemory[];
  };
}

const MemoryRow = React.memo(function MemoryRow({ index, style, data }: MemoryRowProps) {
  const { memories } = data;
  const memory = memories[index];

  if (!memory) return null;

  return (
    <div style={style} role="listitem">
      <MemoryCard memory={memory} />
    </div>
  );
});

export default function MemoryTimeline({ memories }: Props) {
  const listRef = useRef<List>(null);
  // Cache for item sizes to avoid recalculation
  const itemSizeCache = useRef<Map<number, number>>(new Map());

  const sortedMemories = useMemo(() => {
    if (!memories || memories.length === 0) return [];
    return [...memories].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [memories]);

  const coreMemoryCount = useMemo(
    () => sortedMemories.filter((m) => m.is_core_memory).length,
    [sortedMemories]
  );

  // Get item size for virtual list
  const getItemSize = useCallback(
    (index: number) => {
      // Check cache first
      if (itemSizeCache.current.has(index)) {
        return itemSizeCache.current.get(index)!;
      }

      const memory = sortedMemories[index];
      if (!memory) {
        return 120; // Default fallback
      }

      const height = estimateMemoryHeight(memory);
      itemSizeCache.current.set(index, height);
      return height;
    },
    [sortedMemories]
  );

  // Memoize list data to avoid unnecessary re-renders
  const listData = useMemo(
    () => ({ memories: sortedMemories }),
    [sortedMemories]
  );

  if (!memories || memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <Brain className="mb-2 h-8 w-8 opacity-50" />
        <p className="text-sm">No memories recorded yet.</p>
        <p className="mt-1 text-xs">Memories shape who a character becomes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          {sortedMemories.length} {sortedMemories.length === 1 ? 'memory' : 'memories'}
        </span>
        {coreMemoryCount > 0 && (
          <div className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
            <Star className="h-4 w-4 fill-current" />
            <span>{coreMemoryCount} core</span>
          </div>
        )}
      </div>

      <div style={{ height: LIST_HEIGHT }} className="pr-4" role="list" aria-label="Character memories">
        <List
          ref={listRef}
          height={LIST_HEIGHT}
          itemCount={sortedMemories.length}
          itemSize={getItemSize}
          width="100%"
          itemData={listData}
        >
          {MemoryRow}
        </List>
      </div>
    </div>
  );
}
