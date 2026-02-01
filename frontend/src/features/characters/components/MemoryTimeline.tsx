import { useMemo } from 'react';
import { Brain, Star, Calendar, Tag } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { CharacterMemory } from '@/types/schemas';

type Props = {
  memories: CharacterMemory[] | undefined;
};

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

type MemoryCardProps = {
  memory: CharacterMemory;
};

function MemoryCard({ memory }: MemoryCardProps) {
  const isCoreMemory = memory.is_core_memory;

  return (
    <div
      className={`relative p-4 rounded-lg border transition-colors ${
        isCoreMemory
          ? 'border-amber-500/50 bg-amber-500/5'
          : 'border-border bg-card'
      }`}
    >
      {isCoreMemory && (
        <div className="absolute -top-2 -right-2">
          <Star className="h-5 w-5 text-amber-500 fill-amber-500" />
        </div>
      )}

      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span>{formatDate(memory.timestamp)}</span>
          </div>
          <Badge variant="outline" className={IMPORTANCE_COLORS[memory.importance_level]}>
            {memory.importance_level}
          </Badge>
        </div>

        <p className="text-sm leading-relaxed">{memory.content}</p>

        {memory.tags.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
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
}

export default function MemoryTimeline({ memories }: Props) {
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

  if (!memories || memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <Brain className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">No memories recorded yet.</p>
        <p className="text-xs mt-1">Memories shape who a character becomes.</p>
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

      <ScrollArea className="h-[320px] pr-4">
        <div className="space-y-3">
          {sortedMemories.map((memory) => (
            <MemoryCard key={memory.memory_id} memory={memory} />
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
