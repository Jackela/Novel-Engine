/**
 * StoryList - List display of stories
 */
import { useState } from 'react';
import { Filter, Sparkles } from 'lucide-react';
import { Button, Input } from '@/shared/components/ui';
import { LoadingSpinner, EmptyState } from '@/shared/components/feedback';
import { StoryCard } from './StoryCard';
import type { Story, StoryMood } from '@/shared/types/story';

interface StoryListProps {
  stories: Story[];
  isLoading?: boolean;
  onGenerate?: () => void;
  onSelect?: (story: Story) => void;
  onDelete?: (id: string) => void;
  onExport?: (id: string) => void;
}

const moodFilters: { value: StoryMood | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'dramatic', label: 'Dramatic' },
  { value: 'action', label: 'Action' },
  { value: 'mysterious', label: 'Mysterious' },
  { value: 'emotional', label: 'Emotional' },
  { value: 'tense', label: 'Tense' },
  { value: 'calm', label: 'Calm' },
];

export function StoryList({
  stories,
  isLoading = false,
  onGenerate,
  onSelect,
  onDelete,
  onExport,
}: StoryListProps) {
  const [moodFilter, setMoodFilter] = useState<StoryMood | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredStories = stories.filter((story) => {
    const matchesMood = moodFilter === 'all' || story.mood === moodFilter;
    const matchesSearch =
      searchQuery === '' ||
      story.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      story.tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesMood && matchesSearch;
  });

  if (isLoading) {
    return <LoadingSpinner fullScreen text="Loading stories..." />;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <div className="flex gap-1 flex-wrap">
            {moodFilters.map((filter) => (
              <Button
                key={filter.value}
                variant={moodFilter === filter.value ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setMoodFilter(filter.value)}
              >
                {filter.label}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Input
            placeholder="Search stories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full sm:w-64"
          />
          {onGenerate && (
            <Button onClick={onGenerate}>
              <Sparkles className="h-4 w-4 mr-2" />
              Generate
            </Button>
          )}
        </div>
      </div>

      {/* List or Empty State */}
      {filteredStories.length === 0 ? (
        <EmptyState
          title={stories.length === 0 ? 'No stories yet' : 'No matching stories'}
          description={
            stories.length === 0
              ? 'Generate your first story to begin your narrative journey'
              : 'Try adjusting your filters or search query'
          }
          action={
            stories.length === 0 && onGenerate
              ? { label: 'Generate Story', onClick: onGenerate }
              : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredStories.map((story) => (
            <StoryCard
              key={story.id}
              story={story}
              onSelect={onSelect}
              onDelete={onDelete}
              onExport={onExport}
            />
          ))}
        </div>
      )}
    </div>
  );
}
