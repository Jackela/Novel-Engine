/**
 * StoryCard - Display card for a story
 */
import { FileText, Users, Tag, Trash2, Download } from 'lucide-react';
import { Card, CardContent, Badge, Button } from '@/shared/components/ui';
import { cn, formatRelativeTime } from '@/lib/utils';
import type { Story, StoryMood } from '@/shared/types/story';

interface StoryCardProps {
  story: Story;
  onSelect?: (story: Story) => void;
  onDelete?: (id: string) => void;
  onExport?: (id: string) => void;
}

const moodColors: Record<StoryMood, string> = {
  tense: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  calm: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  dramatic: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  mysterious: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  action: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  emotional: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
};

const moodLabels: Record<StoryMood, string> = {
  tense: 'Tense',
  calm: 'Calm',
  dramatic: 'Dramatic',
  mysterious: 'Mysterious',
  action: 'Action',
  emotional: 'Emotional',
};

export function StoryCard({ story, onSelect, onDelete, onExport }: StoryCardProps) {
  return (
    <Card
      className="cursor-pointer transition-all hover:shadow-md"
      onClick={() => onSelect?.(story)}
    >
      <CardContent className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold truncate">{story.title}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge className={cn('text-xs', moodColors[story.mood])}>
                {moodLabels[story.mood]}
              </Badge>
              <span className="text-xs text-muted-foreground">Turn {story.turnNumber}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-1 ml-2">
            {onExport && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={(e) => {
                  e.stopPropagation();
                  onExport(story.id);
                }}
              >
                <Download className="h-4 w-4" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(story.id);
                }}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>

        {/* Summary */}
        <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
          {story.summary || story.content.slice(0, 150) + '...'}
        </p>

        {/* Tags */}
        {story.tags.length > 0 && (
          <div className="flex items-center gap-1 mb-3 flex-wrap">
            <Tag className="h-3 w-3 text-muted-foreground" />
            {story.tags.slice(0, 3).map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
            {story.tags.length > 3 && (
              <span className="text-xs text-muted-foreground">+{story.tags.length - 3}</span>
            )}
          </div>
        )}

        {/* Meta */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span>{story.characters.length} characters</span>
          </div>
          <div className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            <span>{story.events.length} events</span>
          </div>
          <span className="ml-auto">{formatRelativeTime(story.createdAt)}</span>
        </div>
      </CardContent>
    </Card>
  );
}
