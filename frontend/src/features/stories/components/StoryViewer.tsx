/**
 * StoryViewer - Full story content viewer
 */
import { ArrowLeft, Download, Clock, Users, Tag } from 'lucide-react';
import { Button, Badge, Card, CardContent } from '@/shared/components/ui';
import { cn, formatRelativeTime } from '@/lib/utils';
import type { Story, StoryMood, StoryEvent } from '@/shared/types/story';

interface StoryViewerProps {
  story: Story;
  onBack?: (() => void) | undefined;
  onExport?: ((format: 'markdown' | 'pdf' | 'json') => void) | undefined;
}

const moodColors: Record<StoryMood, string> = {
  tense: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  calm: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  dramatic: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  mysterious: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  action: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  emotional: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
};

const eventTypeIcons: Record<StoryEvent['type'], string> = {
  dialogue: '💬',
  action: '⚡',
  discovery: '🔍',
  conflict: '⚔️',
  resolution: '✨',
  transition: '🔄',
};

export function StoryViewer({ story, onBack, onExport }: StoryViewerProps) {
  return (
    <div className="space-y-6">
      <StoryViewerHeader story={story} onBack={onBack} onExport={onExport} />
      <StoryTags tags={story.tags} />
      <StoryContent content={story.content} />
      <StoryEvents events={story.events} />
    </div>
  );
}

type StoryViewerHeaderProps = {
  story: Story;
  onBack?: (() => void) | undefined;
  onExport?: ((format: 'markdown' | 'pdf' | 'json') => void) | undefined;
};

function StoryViewerHeader({ story, onBack, onExport }: StoryViewerHeaderProps) {
  return (
    <div className="flex items-start justify-between">
      <div className="flex items-center gap-4">
        {onBack && (
          <Button variant="ghost" size="icon" onClick={onBack}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
        )}
        <div>
          <h1 className="text-2xl font-bold">{story.title}</h1>
          <div className="mt-2 flex items-center gap-3 text-sm text-muted-foreground">
            <Badge className={cn('text-xs', moodColors[story.mood])}>
              {story.mood}
            </Badge>
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Turn {story.turnNumber}
            </span>
            <span className="flex items-center gap-1">
              <Users className="h-3 w-3" />
              {story.characters.length} characters
            </span>
            <span>{formatRelativeTime(story.createdAt)}</span>
          </div>
        </div>
      </div>

      {onExport && (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onExport('markdown')}>
            <Download className="mr-2 h-4 w-4" />
            Markdown
          </Button>
          <Button variant="outline" size="sm" onClick={() => onExport('pdf')}>
            <Download className="mr-2 h-4 w-4" />
            PDF
          </Button>
        </div>
      )}
    </div>
  );
}

function StoryTags({ tags }: { tags: Story['tags'] }) {
  if (tags.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Tag className="h-4 w-4 text-muted-foreground" />
      {tags.map((tag) => (
        <Badge key={tag} variant="outline">
          {tag}
        </Badge>
      ))}
    </div>
  );
}

function StoryContent({ content }: { content: string }) {
  return (
    <Card>
      <CardContent className="p-6">
        <div className="prose prose-sm dark:prose-invert max-w-none">
          {content.split('\n\n').map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function StoryEvents({ events }: { events: Story['events'] }) {
  if (events.length === 0) {
    return null;
  }

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">Story Events</h2>
      <div className="space-y-3">
        {events.map((event) => (
          <Card key={event.id}>
            <CardContent className="flex items-start gap-3 p-4">
              <span className="text-xl">{eventTypeIcons[event.type]}</span>
              <div className="flex-1">
                <div className="mb-1 flex items-center gap-2">
                  <Badge variant="outline" className="text-xs capitalize">
                    {event.type}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
                <p className="text-sm">{event.description}</p>
                {event.involvedCharacters.length > 0 && (
                  <div className="mt-2 flex items-center gap-1 text-xs text-muted-foreground">
                    <Users className="h-3 w-3" />
                    {event.involvedCharacters.join(', ')}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
