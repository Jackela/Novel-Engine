/**
 * NarrativeOutput - Display generated narrative content
 */
import { ScrollText, Users, Calendar, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import { Card, CardContent, Badge, Button } from '@/shared/components/ui';
import { cn, formatRelativeTime } from '@/shared/lib/utils';
import type { NarrativeOutput as NarrativeOutputType } from '@/shared/types/orchestration';

interface NarrativeOutputProps {
  narratives: NarrativeOutputType[];
  maxVisible?: number;
}

export function NarrativeOutput({ narratives, maxVisible = 3 }: NarrativeOutputProps) {
  const [expanded, setExpanded] = useState(false);
  const visibleNarratives = expanded ? narratives : narratives.slice(0, maxVisible);
  const hasMore = narratives.length > maxVisible;

  if (narratives.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <ScrollText className="h-12 w-12 mx-auto text-muted-foreground mb-3" />
          <h3 className="font-medium mb-1">No narrative yet</h3>
          <p className="text-sm text-muted-foreground">
            Start the orchestration to generate narrative content
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <ScrollText className="h-5 w-5" />
          Narrative Output
        </h3>
        <Badge variant="outline">{narratives.length} entries</Badge>
      </div>

      <div className="space-y-3">
        {visibleNarratives.map((narrative, index) => (
          <NarrativeCard
            key={narrative.id}
            narrative={narrative}
            isLatest={index === 0}
          />
        ))}
      </div>

      {hasMore && (
        <Button
          variant="ghost"
          className="w-full"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-4 w-4 mr-2" />
              Show Less
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4 mr-2" />
              Show {narratives.length - maxVisible} More
            </>
          )}
        </Button>
      )}
    </div>
  );
}

interface NarrativeCardProps {
  narrative: NarrativeOutputType;
  isLatest?: boolean;
}

function NarrativeCard({ narrative, isLatest = false }: NarrativeCardProps) {
  const [showFull, setShowFull] = useState(isLatest);
  const isLong = narrative.content.length > 500;

  return (
    <Card className={cn(isLatest && 'border-primary')}>
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Badge variant={isLatest ? 'default' : 'secondary'}>
              Turn {narrative.turnNumber}
            </Badge>
            {isLatest && (
              <Badge variant="outline" className="text-xs">
                Latest
              </Badge>
            )}
          </div>
          <span className="text-xs text-muted-foreground">
            {formatRelativeTime(narrative.timestamp)}
          </span>
        </div>

        {/* Content */}
        <div className="prose prose-sm dark:prose-invert max-w-none mb-3">
          {showFull || !isLong ? (
            narrative.content.split('\n\n').map((para, i) => (
              <p key={i}>{para}</p>
            ))
          ) : (
            <>
              <p>{narrative.content.slice(0, 500)}...</p>
              <Button
                variant="link"
                className="p-0 h-auto"
                onClick={() => setShowFull(true)}
              >
                Read more
              </Button>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span>{narrative.characters.length} characters</span>
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>{narrative.events.length} events</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
